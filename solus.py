#!/usr/bin/env python
from __future__ import print_function, unicode_literals, division
from argparse import ArgumentParser, ArgumentError

import binascii
import cv2
import functools
import itertools
import numpy as np
import struct
import sys
import types

__author__ = "GoodiesHQ"

CHAN_SIZE   = 8     # Number of bits per channel.
PROLOG_SIZE = 2     # Number of pixels used for the prologue.
LEN_SIZE    = 4     # number of bytes that store the length of data
CHAN_CNT    = 3     # Number of channels (R,G,B)
PNG_COMP    = 4     # Default PNG compression value

# Exceptions

class UnexpectedXOR(Exception):
    """An XOR key was provided, but none was expected"""
    pass


class InvalidImage(Exception):
    """The image provided is either not a valid image (encoding) or was not encoded using this utility (decoding)."""
    pass


class TooMuchData(Exception):
    """The image is not able to store all of the data."""
    pass


class InvalidLSB(Exception):
    """The provided LSB value is invalid"""
    pass


class InvalidXOR(Exception):
    """The XOR key provided is invalid"""
    pass


class MissingXOR(Exception):
    """An XOR key was expected, but none was provided"""
    pass


class LSBCodec(object):
    """
    The base class for the LSB Encoder and Decoder. Provides basic iteration through pixels and
    several static methods for bitmask generation, xor encryption, and data conversion.
    """

    XOR_Y = 0b111000    # an XOR key is expected
    XOR_N = 0b000000    # an XOR key is not expected

    def __init__(self, filename):
        self._img = cv2.imread(filename)
        if self._img is None:
            raise InvalidImage
        self._h, self._w, _ = self._img.shape

    def iter_pixels(self):
        """A generator that iterates through the pixels of the provided image."""
        for h in range(self._h):
            for w in range(self._w):
                yield h, w, self.img[h, w]

    @staticmethod
    def xor(data, key):
        """A python2/3 compatible xor function for bytes.
        :data   bytes, the data to be encoded
        :key    bytes, the encryption/decryption key
        """
        return bytes(bytearray(
            d ^ k for d, k in zip(bytearray(data), itertools.cycle(bytearray(key)))
        ))

    def save(self, filename, compression=PNG_COMP):
        """Saves and compresses the instance's image as 'filename'."""

        if compression > 9 or compression < 0:
            compression = PNG_COMP

        if "." not in filename:
            filename += ".png"

        ext = filename.split(".")[-1].lower()

        if ext in ("png",):
            args = [[int(cv2.IMWRITE_PNG_COMPRESSION), compression]]
        else:
            args = []

        cv2.imwrite(filename, self.img, *args)

    def available(self, lsb_cnt):
        return ((self.img.size - PROLOG_SIZE) // (CHAN_SIZE // lsb_cnt)) - LEN_SIZE - 1

    @staticmethod
    def genmask(size):
        """Generate a bitmask shifted 'size' bits."""
        assert size <= CHAN_SIZE, "Masks should not be greater than the number of bits in a channel"
        return 1 << size

    @staticmethod
    def gen1mask(size):
        """Generate a bitmask consisting of 'size' consecutive 1's."""
        mask = 0
        for i in range(size):
            mask |= LSBCodec.genmask(i)
        return mask

    @staticmethod
    def gen0mask(size):
        """Generates a bitmask of CHAN_SIZE bits with 'size' trailing 0's."""
        return LSBCodec.gen1mask(CHAN_SIZE) ^ LSBCodec.gen1mask(size)

    @staticmethod
    def bytes_to_int(b):
        return int(binascii.hexlify(b), 16)

    @staticmethod
    def int_to_bytes(i, size=0):
        return binascii.unhexlify("{:x}".format(i).zfill(size * 2))

    @property
    def img(self):
        return self._img

class LSBDecoder(LSBCodec):
    def __init__(self, img):
        super(LSBDecoder, self).__init__(img)

    def _decode_data(self, shifts, lsb_cnt, piter):
        value = 0
        pos = 0
        m0, m1 = self.gen0mask(lsb_cnt), self.gen1mask(lsb_cnt)
        while shifts:
            h, w, px = next(piter)
            for c in range(CHAN_CNT):
                if not shifts:
                    break
                value |= int(px[c] & m1) << (pos * lsb_cnt)
                pos += 1
                shifts -= 1
        return value

    def decode(self, xor_key=None):
        if not isinstance(xor_key, (bytes, types.NoneType)):
            raise TypeError("Only bytes can be used as xor keys.")
        piter = self.iter_pixels()
        m0, m1 = self.gen0mask(CHAN_CNT), self.gen1mask(CHAN_CNT)
        prolog = self._decode_data(PROLOG_SIZE * CHAN_CNT, 1, piter)
        xor, lsb_cnt = prolog & m0, prolog & m1
        try:
            if xor not in (self.XOR_Y, self.XOR_N):
                raise InvalidXOR
            lsb_cnt = lsb_check(lsb_cnt)
        except (InvalidXOR, InvalidLSB):
            raise ValueError("The image provided is invalid.")
        if xor == self.XOR_Y and xor_key is None:
            raise MissingXOR
        size = self._decode_data(LEN_SIZE * CHAN_SIZE // lsb_cnt, lsb_cnt, piter)
        print("Decoding {} bytes.".format(size))
        data = self._decode_data(size * CHAN_SIZE // lsb_cnt, lsb_cnt, piter)
        data = self.int_to_bytes(data, size)
        if xor == self.XOR_Y:
            data = self.xor(data, xor_key)
        return data

class LSBEncoder(LSBCodec):
    """
    Contains the image, offsets, and mask values.
    """

    def __init__(self, filename):
        super(LSBEncoder, self).__init__(filename)

    def _encode_data(self, value, shifts, lsb_cnt, piter):
        m0, m1 = self.gen0mask(lsb_cnt), self.gen1mask(lsb_cnt)
        print("Encoding with {} shifts...".format(shifts))
        while shifts:
            h, w, px = next(piter)
            for c in range(CHAN_CNT):
                if not shifts:
                    break
                px[c] = (px[c] & m0) | (value & m1)
                shifts -= 1
                value >>= lsb_cnt
            self._img[h,w] = px

    def encode(self, data, lsb_cnt=1, xor_key=None):
        if not isinstance(data, bytes):
            raise TypeError("Only bytes can be encoded.")
        if not isinstance(xor_key, (bytes, type(None))):
            raise TypeError("Only bytes can be used as xor keys.")

        assert lsb_check(lsb_cnt)
        piter = self.iter_pixels()
        size = len(data)
        print("Encoding {} bytes.".format(size))

        if size > self.available(lsb_cnt):
            raise TooMuchData

        if xor_key is not None:
            data = self.xor(data, xor_key)
        data = self.bytes_to_int(data)

        prolog = (self.XOR_N if xor_key is None else self.XOR_Y) | lsb_cnt

        self._encode_data(prolog, PROLOG_SIZE * CHAN_CNT, 1, piter)
        self._encode_data(size, LEN_SIZE * CHAN_SIZE // lsb_cnt, lsb_cnt, piter)
        self._encode_data(data, size * CHAN_SIZE // lsb_cnt, lsb_cnt, piter)

    def encode_string(self, string, xor_key=None):
        return self.encode(string.encode(), xor_key)

    def encode_file(self, filename, xor_key=None):
        with open(filename, "rb") as f:
            data = f.read()
        return self.encode(data, xor_key)

def lsb_check(bits):
    bits = int(bits)
    # if not bits or CHAN_SIZE % bits or bits >= CHAN_SIZE:
    if bits > CHAN_SIZE or bits <= 0:
        raise InvalidLSB
    return bits

def to_bytes(s):
    return s.encode() if isinstance(s, str) else s if isinstance(s, bytes) else None

def main():
    ap = ArgumentParser(prog="LSB")
    sp = ap.add_subparsers(dest="operation", help="Help for subcommand")
    sp.required = True
    enc = sp.add_parser("e", help="Encodes data into an image.")
    dec = sp.add_parser("d", help="Decodes data from an image.")
    shw = sp.add_parser("s", help="Show the current image")

    enc.add_argument("--bits", type=lsb_check, default=1, help="Number of least significant bits used per px.")
    enc.add_argument("--xor", type=to_bytes, default=None, help="The XOR key used to encrypt data.")
    enc.add_argument("--img", type=str, required=True, help="File in which to hide encoded data.")
    enc.add_argument("--out", type=str, default=None, help="Output file to store the encoded data.")
    enc.add_argument("--compression", type=int, default=PNG_COMP, help="Output PNG Compression (0-9, default: {})".format(PNG_COMP))

    grp = enc.add_mutually_exclusive_group(required=True)
    grp.add_argument("--string", type=to_bytes, help="Encode a string into an image file.")
    grp.add_argument("--file", type=str, help="Encode a binary file into an image file.")

    dec.add_argument("--xor", type=to_bytes, default=None, help="The XOR key used to decrypt data.")
    dec.add_argument("--img", type=str, required=True, help="File from which to extract encoded data.")
    dec.add_argument("--out", type=str, required=True, help="Output file to store the decoded data.")

    shw.add_argument("--img", type=str, required=True, help="File to display the pixel matrix.")

    args = ap.parse_args()

    def encode():
        enc = LSBEncoder(args.img)
        if args.string is None:
            with open(args.file, "rb") as fin:
                data = fin.read()
        else:
            data = args.string
        filename = args.out or (''.join(args.img.split(".")[:-1]) + "_enc.png")
        if not filename.lower().endswith(".png"):
            filename += ".png"
        enc.encode(data, args.bits, args.xor)
        print("Encoding finished. Compressing and saving...")
        enc.save(filename, args.compression)

    def decode():
        dec = LSBDecoder(args.img)
        data = dec.decode(args.xor)
        with open(args.out, "wb") as fout:
            fout.write(data)

    def show():
        print(cv2.imread(args.img))

    {
        "e": encode,
        "d": decode,
        "s": show,
    }.get(args.operation)()

if __name__ == "__main__":
    main()
