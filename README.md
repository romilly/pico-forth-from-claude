# Raspberry Pi Pico FORTH VM

## Update ##

It turns out that this implementation is riddeld with errors. I'm working on a replacement.

Don't use this code!

### Bad code follows.

A lightweight FORTH programming language implementation for the Raspberry Pi Pico, developed in Python.

If you're not familiar with FORTH, here's a quick overview:

FORTH is a stack-based programming language that emphasizes simplicity and extensibility. This implementation provides a lightweight version suitable for microcontrollers like the Raspberry Pi Pico.

You can learn the basics of the language from the free online version of Leon Broadies's classic [Starting FORTH](https://www.forth.com/starting-forth/). 

There's a short [video demonstration](https://youtu.be/fXhMrK3_kTY) on YouTube

## Installation

To install this FORTH VM on your Raspberry Pi Pico:

1. Install the [Thonny IDE](https://thonny.org/) if you haven't already
2. Connect your Raspberry Pi Pico to your computer via USB
3. Open Thonny IDE and select "Raspberry Pi Pico" as the interpreter:
   - Go to Tools > Options > Interpreter
   - Select "MicroPython (Raspberry Pi Pico)"
4. Copy the FORTH VM code into a new file
5. Save the file to your Pico as "main.py" (to run at startup) or any other name like "forth.py"
6. Run the program either by clicking the Run button or by saving it as main.py and resetting the Pico

## Basic Usage

Here are some example FORTH programs to test with the VM:

### 1. Basic arithmetic
```forth
3 4 + .
```
Output: `7`

### 2. Stack manipulation
```forth
1 2 3 .S
```
Output: `[ 1 2 3 ]`
```forth
DROP .S
```
Output: `[ 1 2 ]`
```forth
SWAP .S
```
Output: `[ 2 1 ]`
```forth
DUP .S
```
Output: `[ 2 1 1 ]`

### 3. Define a word to square a number
```forth
: SQUARE DUP * ;
5 SQUARE .
```
Output: `25`

### 4. Define a word to calculate factorial
```forth
: FACTORIAL DUP 1 > IF DUP 1 - FACTORIAL * ELSE DROP 1 THEN ;
5 FACTORIAL .
```
Output: `120`

### 5. Print a simple message
```forth
: HELLO 72 EMIT 101 EMIT 108 EMIT 108 EMIT 111 EMIT 33 EMIT CR ;
HELLO
```
Output: `Hello!`

### 6. Using the ." (dot-quote) word for string printing
```forth
." Hello, FORTH world!"
```
Output: `Hello, FORTH world!`

```forth
: GREET ." Welcome to Pico FORTH! " ;
GREET
```
Output: `Welcome to Pico FORTH! `

### 7. Create a loop to count from 1 to 5
```forth
: COUNT 1 5 DO I . LOOP ;
COUNT
```
Output: `1 2 3 4`

## Hardware Integration

The FORTH VM can be extended to control Pico hardware by adding primitive words that interface with MicroPython's machine module.

### Example: Adding Hardware Primitives

```python
from forth_vm import ForthVM
import machine
import time

# Create a custom FORTH VM with hardware primitives
def create_hardware_forth():
    forth = ForthVM()
    
    # Add GPIO primitives
    forth.add_primitive("PIN-OUT", lambda vm: pin_out(vm))
    forth.add_primitive("PIN-IN", lambda vm: pin_in(vm))
    forth.add_primitive("PIN-HIGH", lambda vm: pin_high(vm))
    forth.add_primitive("PIN-LOW", lambda vm: pin_low(vm))
    forth.add_primitive("PIN-READ", lambda vm: pin_read(vm))
    forth.add_primitive("MS", lambda vm: ms_delay(vm))
    
    return forth

# Primitive implementations for GPIO control
def pin_out(vm):
    """( pin# -- ) Configure a GPIO pin as output"""
    pin_num = vm.pop()
    pin = machine.Pin(pin_num, machine.Pin.OUT)
    # Store pin object in a dictionary to reference later
    if not hasattr(vm, 'pins'):
        vm.pins = {}
    vm.pins[pin_num] = pin

# Additional primitive implementations...
```

### Hardware Control Examples

#### 1. Blink an LED on pin 25 (Pico's built-in LED)
```forth
25 PIN-OUT
: BLINK 25 PIN-HIGH 500 MS 25 PIN-LOW 500 MS ;
: BLINK-TIMES 0 DO BLINK LOOP ;
5 BLINK-TIMES
```

#### 2. Read a button on pin 15 and light LED when pressed
```forth
15 PIN-IN
25 PIN-OUT
: BUTTON-LED 15 PIN-READ IF 25 PIN-HIGH ELSE 25 PIN-LOW THEN ;
: MONITOR BEGIN BUTTON-LED 100 MS AGAIN ;
MONITOR
```

## Customization

Customize the VM for your specific needs:

### 1. Memory management
- Adjust stack sizes in the ForthVM.__init__ method
- For very constrained memory, reduce MAX_CODE_SIZE

### 2. Add application-specific primitives
- Define Python functions for your primitives
- Add them to the VM using add_primitive()

### 3. Persistent dictionary
- Add code to save/load dictionary to/from flash storage
- This allows saving FORTH definitions between reboots

### Example: Saving/Loading Dictionary to Flash

```python
def save_dictionary(forth, filename="forth_dict.txt"):
    try:
        with open(filename, "w") as f:
            for word in forth.user_words():  # Hypothetical method to get user-defined words
                f.write(word + "\n")
        print(f"Dictionary saved to {filename}")
    except Exception as e:
        print(f"Error saving dictionary: {e}")

def load_dictionary(forth, filename="forth_dict.txt"):
    try:
        with open(filename, "r") as f:
            for line in f:
                forth.interpret(line.strip())
        print(f"Dictionary loaded from {filename}")
    except Exception as e:
        print(f"Error loading dictionary: {e}")
