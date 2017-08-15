# Solus
A Python2/3 compatible utility for encoding arbitrary data in an image via Least Significant Bit (LSB) steganography using OpenCV.

### What is LSB Steganography?
LSB Stego uses the fact that altering the least significant bits of data changes the final output in a very minor way, and allows for storing arbitrary data. LSB Stego, as it pertains to images, refers to altering the least significant bit(s) of the RGB (Red, Green, Blue) channel values in order to construct a value that can be retrieved later. Ideally, the encoded image should be virtually indistinguishable from the original, and the entropy of the file should not increase a significant amount.

### That sounds cool, but I don't understand.
The concept of *significance*, as it relates to numbers, refers to the amount that a value will change if one of its digit is changed. Take base-10 (decimal), for example. The number `2187` has four digits. If you were to alter any of the digits by one value, how large would effect changes be?

- Changing the `2` will change the final number by 1000 units.
- Changing the `1` will change the final number by 100 units.
- Changing the `8` will change the final number by 10 units.
- Changing the `7` will change the final number by 1 unit.

In short, **the further left a digit is, the more significant it is.** This holds true regardless of the representation of the number (decimal, hex, binary, etc.). The goal of LSB stegonography is to change the least significant numbers to a desired value that will allow us to later extract it and re-construct our original data.

### I get the significance, but I need an example.
Fair enough. Say we wanted to store the letter 'H' into some image comprised of 3 pixels. Three randomly generated colors:<br>
<img src="https://placehold.it/21/A7DDF8/000000?text=+" /><img src="https://placehold.it/21/24C2C4/000000?text=+" /><img src="https://placehold.it/21/9197D4/000000?text=+" />

The ASCII value of `H` is `0x48`. In binary, this is `01001000`.

<table>
  <tr>
    <td>Color</td>
    <td>Hex</td>
    <td>RGB (Hex)</td>
    <td>RGB (Dec)</td>
    <td>RGB (Bin)</td>
  <tr>
  <tr>
    <td><img src="https://placehold.it/21/A7DDF8/000000?text=+" /></td>
    <td>#a7ddf8</td>
    <td>(a7, dd, f8)</td>
    <td>(167, 221, 248)</td>
    <td>(1010011<b>1</b>, 1101110<b>1</b>, 1111100<b>0</b>)</td>
  </tr>
  <tr>
    <td><img src="https://placehold.it/21/24C2C4/000000?text=+" /></td>
    <td>#24c2c4</td>
    <td>(24, c2, c4)</td>
    <td>(36, 194, 196)</td>
    <td>(0010010<b>0</b>, 1100001<b>0</b>, 1100010<b>0</b>)</td>
  </tr>
  <tr>
    <td><img src="https://placehold.it/21/9197D4/000000?text=+" /></td>
    <td>#9197d4</td>
    <td>(91, 97, d4)</td>
    <td>(145, 151, 212)</td>
    <td>(1001000<b>1</b>, 1001011<b>1</b>, 1101010<b>0</b>)</td>
  </tr>
</table>

In bold, I've identified the least significant bit of each number. Because we're only using the last bit, this is referred to as LSB-1. If we used the last two bits, then it would be LSB-2, and so on. The more bits you use, the more data you can store, but the more each pixel can potentially change, leading to noticeable fuzzing or discoloration of the image.

In order to store the aforementioned `H` value (`01001000`) into these pixels, we simply change the last bit of each channel to match up with the data that we want to store. Some will be changed, some will not. Each byte that we would like to encode requires 8 channels in LSB-1 (4 channels in LSB-2 since it is 2 bits per channel, etc.). In this example, there is a remaining channel that is not used. It should be noted that **Solus** is perfectly capable of handling an arbitrary channel size, LSB count (LSB-1, LSB-2, LSB-3, LSB-4, etc), and byte length. It does not skip channels until the very end of the data stream, allowing for the most compact storage.

<table>
  <tr>
    <td>Original</td>
    <td>Last Bit</td>
    <td>Altered</td>
  </tr>
  <tr>
    <td>1010011<b>1</b></td>
    <td>1 -> 0</td>
    <td>1010011<b>0</b></td>
  </tr>
  <tr>
    <td>1101110<b>1</b></td>
    <td>1 -> 1</td>
    <td>1101110<b>1</b></td>
  </tr>
  <tr>
    <td>1111100<b>0</b></td>
    <td>0 -> 0</td>
    <td>1111100<b>0</b></td>
  </tr>
  <tr>
    <td>0010010<b>0</b></td>
    <td>0 -> 0</td>
    <td>0010010<b>0</b></td>
  </tr>
  <tr>
    <td>1100001<b>0</b></td>
    <td>0 -> 1</td>
    <td>1100001<b>1</b></td>
  </tr>
  <tr>
    <td>1100010<b>0</b></td>
    <td>0 -> 0</td>
    <td>1100010<b>0</b></td>
  </tr>
  <tr>
    <td>1001000<b>1</b></td>
    <td>1 -> 0</td>
    <td>1001000<b>0</b></td>
  </tr>
  <tr>
    <td>1001011<b>1</b></td>
    <td>1 -> 0</td>
    <td>1001011<b>0</b></td>
  </tr>
  <tr>
    <td>11010100</td>
    <td>N/A</td>
    <td>11010100</td>
  </tr>
</table>

Notice that the last bits of the channels, put together, equal `01001000` (`H`) which is the very same data that we wanted to encode. All thats left is to put these back into their hex color codes. Here are the new values:

<table>
  <tr>
    <td>Color</td>
    <td>Hex</td>
    <td>RGB (Hex)</td>
    <td>RGB (Dec)</td>
    <td>RGB (Bin)</td>
  <tr>
  <tr>
    <td><img src="https://placehold.it/21/A6DDF8/000000?text=+" /></td>
    <td>#a6ddf8</td>
    <td>(a6, dd, f8)</td>
    <td>(166, 221, 248)</td>
    <td>(1010011<b>0</b>, 1101110<b>1</b>, 1111100<b>0</b>)</td>
  </tr>
  <tr>
    <td><img src="https://placehold.it/21/24C3C4/000000?text=+" /></td>
    <td>#24c3c4</td>
    <td>(24, c3, c4)</td>
    <td>(36, 195, 196)</td>
    <td>(0010010<b>0</b>, 1100001<b>1</b>, 1100010<b>0</b>)</td>
  </tr>
  <tr>
    <td><img src="https://placehold.it/21/9096D4/000000?text=+" /></td>
    <td>#9096d4</td>
    <td>(90, 96, d4)</td>
    <td>(144, 150, 212)</td>
    <td>(1001000<b>0</b>, 1001011<b>0</b>, 1101010<b>0</b>)</td>
  </tr>
</table>

Here you can see a comparisson between the original pixels and the altered ones (noticeable? not at all):<br>
<img src="https://placehold.it/21/A7DDF8/000000?text=+" /><img src="https://placehold.it/21/24C2C4/000000?text=+" /><img src="https://placehold.it/21/9197D4/000000?text=+" /><br>
<img src="https://placehold.it/21/A6DDF8/000000?text=+" /><img src="https://placehold.it/21/24C3C4/000000?text=+" /><img src="https://placehold.it/21/9096D4/000000?text=+" />


### OK, that's pretty cool, but when would I possibly use this?
Steganography provides the ability for data to 'hide in plain sight.' Properly performed, this type of steganography can be used to securely and invisibly hide (and encrypt) any type of data within an image, and still allow the image to be subsequently shared over a completely public medium such as [Imgur](https://imgur.com/), [Facebook](https://facebook.com), [Instagram](https://instagram.com), or similar, without anyone knowing that data is hidden inside. When XOR encryption is used, it will be virtually impossible for an analyst to determine that data is hidden inside, let alone the contents of the data. In theory, this could be used to share private information, passwords, private keys, of anything else in the event that a communication channel is monitored or infiltrated. It may also be used to transmit sensitive information outside of government-monitored network, or to covertly distribute malicious commands to a botnet that receives its instructions from a public Instagram account, or simply just to impress your friends. 

**Note:** while this utility will accept JPEG, PNG, BMP, and various other image types, it will output images as PNG due to the lossless compression algorithms used that do not alter any pixels (JPEG, for example, has lossy compression).
