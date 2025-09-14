# discord-bobbin-bot

## Introduction

Hello! This is the README for the **discord-bobbin-bot** project. It provides a bot interface on discord, to the [**bobbin**](https://github.com/micahcowan/bobbin) text-oriented Apple \]\[ emulator. Specifically, this bot enables you to send a text script to an emulated Apple \]\[, just as if you were typing the script into the keyboard of an Apple \]\[ machine. The bot will run your script, and send you the text-output response from the emulated Apple \]\[.

### What can you do?

- Interface with the bot in approved channels, or via direct message
- Try out direct commands in AppleSoft, to remind yourself how something works
- Send an AppleSoft or Integer ("Woz") BASIC program to be executed
- Enter the monitor program and
  - Run a short session with an emulated Apple \]\[, \]\[+, or enhanced or unenhanced Apple //e. 
  - Inspect or modify the Apple \]\['s RAM
  - Run or disassemble a firmware ROM routine
  - Enter and run a program, optionally using the mini-assembler

### What can't you do?

- Output any kind of graphics
- Produce output of more than 30 lines, or 1900 characters (to mitigate the opportunity for spamming a channel)
- Run a program or routine that would take more than 2 minutes to run on the real machine (it will only take a few seconds for the bot to run)
- Run an interactive session with the emulated Apple
- Run a session across multiple separate messages
- Use disk images or data cassette tapes
 - In the future, if there is interest, I may elect to boot the machine with ProDOS loaded into RAM. It will still not emulate a disk drive, but the `/RAM` volume would be available. This could be useful for testing ProDOS commands within AppleSoft BASIC.
- Use the RESET key
- Enter arbitrary control characters that can't be typed into a Discord message
- Use either the open- or closed-Apple keys (nor joystick or paddle fire buttons)

## How to use

### Direct messaging

If the **bobbin** user resides on your Discord server, you can send a direct message to **bobbin** with input text, and **bobbin** will reply with the output result.
Example:
```
for i=1 to 3 : print spc(i);"HELLO" : next
```
The reply will be:
```
 HELLO
  HELLO
   HELLO
```
(**Note:** the AppleSoft `TAB()` function for `PRINT` statements will not work - try using the `SPC()` function instead (as in the example above).)

Note that the input text is not echoed, nor are the prompt characters you would see on a real Apple \]\['s screen.

It is recommended, but not required, to begin and end your messages to **bobbin** with \`\`\`, on a line all on its own. The bot will strip it out&mdash;but only if it's on the first or last line of your message. Typing this causes Discord to format your message in a way that makes more sense for program input&mdash;but *also*, typing Enter in your message will not close and send the message until you terminate the \`\`\` block, which makes it much easier to avoid accidentally typing an Enter before you've finished typing the bot's input message. If you do *not* use \`\`\`, then you must remember to hold the Shift key down while you type the Enter for each line, in order to avoid sending your message prematurely.

### Mentions and Tags

If the bot is configured to respond on certain channels in your server, you may also begin any channel message with `!bobbin` in order to get the bot's attention; or you can type `@bobbin` followed by the Tab key, to &ldquo;mention&rdquo; bobbin. This must happen on the very first line of your message, and nowhere else. If you use the \`\`\` block, it must occur on the line *following* the `!bobbin` or `@bobbin`

Please note that after typing `@bobbin`, you *must* follow that with a Tab keypress. At the time of this writing, f you instead type a Space, it will not appear to the bot that it has been mentioned, and so it will not respond. `!bobbin` is a more reliable means of attracting the bot's attention, so it is the recommended method.

### Emulation Options

#### `m:`*machine*

Currently there is a single option that can be provided to the bot, governing what flavor of Apple \]\[ machine it will emulate. By default, the bot will select an Enhanced Apple //e for the emulation. On the initial `!bobbin` line, you can add `m:plus`, and it will emulate an Apple \]\[+ instead.

Here is a list of the Apple \]\[ machine flavors that the bot can emulate, along with the list of allowed arguments to the `m:` option that will select that machine flavor.

##### Apple \]\[+ (64k/Language Card)

Follow the `m:` option with any of: `plus`, `+`, `][+`, `ii+`, `twoplus`, `autostart`, `applesoft`, or `asoft`. There is no difference between these values&mdash;pick one you like!

This will boot you into a machine that has no lowercase support (you can still enter them&mdash;the emulator will translate them to uppercase). There is no miniassembler available.

##### Original Apple \]\[ running Integer (Woz) BASIC (64k)

Follow the `m:` option with any of: `original`, `][`, `ii`, `two`, `woz`, `int`, or `integer`.

Note that, unlike a *real* original Apple \]\[, the emulator will boot directly into Integer BASIC, and not the firmware monitor program. To reach the monitor, you can still of course use `CALL -151`. A miniassembler is accessible from the monitor with the command `F666G`. Note that, since the Reset key is not available, you cannot use it to exit the miniassembler. But you can type `$FF59G` to return to the monitor, as a workaround.

This machine configuration has 64k of RAM, 16k of which is accessed as if it had a "Language Card" installed&mdash;but the firmware ROM is still that of the original (no autostart ROM).

##### Unenhanced Apple \]\[e

Follow the `m:` option with any of: `twoey`, `][e`, or `iie`.

**WARNING**: This machine is not recommended for most purposes. In particular, it is the only emulated machine option that *will not* process lowercase characters in AppleSoft commands (inside strings or `DATA` statements is still fine). The \]\[ and the \]\[+ have no support for lowercase characters, but the emulator will uppercase them for you. The enhanced //e will happily accept AppleSoft commands written in lowercase. Only the unenhanced Apple \]\[e both has lowercase characters, and also requires uppercase in its AppleSoft commands.

No miniassembler is available.

##### Enhanced Apple //e

Follow the `m:` option with either `enhanced` or  `//e`. Or leave out the `m:` option entirely&mdash;this is the default configuration.

A miniassembler is available by typing `!` in the monitor (`CALL -151`). Type a blank line to return to the monitor.

#### Exiting the Monitor (`CALL -151` routine)

##### Equivalent to Reset

You cannot type Reset. You also cannot type a Control-B or Control-C. This leaves you with none of the usual means for exiting the monitor program. In place of typing Reset, you can jump to whatever address is located at `FFFC.FFFD`:

```
!bobbin m:enhanced
CALL-151
E000.E007
FFFC.FFFD
FA62G

print "hello!"
```

(Result:)
```
E000- 4C 28 F1 4C 3C D4 C4 20
FFFC- 62 FA
hello!
```

Or for a more portable approach:
```
CALL-151
300:4C
301<FFFC.FFFDM
300.302L
300G

print "hello!"
```

(Result:)
```
0300-   4C 62 FA    JMP   $FA62
[...]  
hello!
```

##### Control-B, Control-C

To do a cold-start into BASIC (equivalent to Control-B), use `E000G`; for warm-start (preserving any existing programs; equivalent to Control-C), use `E003G`
