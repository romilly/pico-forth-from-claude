"""
FORTH Virtual Machine for Raspberry Pi Pico
Implemented in MicroPython with 16-bit cell size optimizations
"""

class ForthVM:
    def __init__(self):
        # Memory configuration - optimized for constrained environment
        self.STACK_SIZE = 64
        self.RETURN_STACK_SIZE = 32
        self.DICT_SIZE = 128
        self.MAX_CODE_SIZE = 1024
        self.MAX_WORD_SIZE = 16
        
        # Data stack and return stack
        self.stack = [0] * self.STACK_SIZE
        self.sp = 0  # Stack pointer
        
        self.return_stack = [0] * self.RETURN_STACK_SIZE
        self.rsp = 0  # Return stack pointer
        
        # Dictionary for word definitions
        # Each entry: (name, immediate_flag, code_pointer or function, is_primitive)
        self.dictionary = []
        
        # Code space for user-defined words
        self.code_space = [0] * self.MAX_CODE_SIZE
        self.code_idx = 0
        
        # Interpreter state
        self.running = True
        self.compiling = False
        self.current_word = None
        
        # Input buffer
        self.input_buffer = ""
        self.input_pos = 0
        
        # Error handling
        self.last_error = None
        
        # Initialize with built-in words
        self._init_primitives()
    
    # Stack Operations
    def push(self, value):
        """Push a value onto the data stack"""
        if self.sp >= self.STACK_SIZE:
            self._error("Stack overflow")
            return
        
        # Enforce 16-bit cells
        value = value & 0xFFFF if value >= 0 else value | 0xFFFF0000
        self.stack[self.sp] = value
        self.sp += 1
    
    def pop(self):
        """Pop a value from the data stack"""
        if self.sp <= 0:
            self._error("Stack underflow")
            return 0
        
        self.sp -= 1
        return self.stack[self.sp]
    
    def rpush(self, value):
        """Push a value onto the return stack"""
        if self.rsp >= self.RETURN_STACK_SIZE:
            self._error("Return stack overflow")
            return
        
        # Enforce 16-bit cells
        value = value & 0xFFFF if value >= 0 else value | 0xFFFF0000
        self.return_stack[self.rsp] = value
        self.rsp += 1
    
    def rpop(self):
        """Pop a value from the return stack"""
        if self.rsp <= 0:
            self._error("Return stack underflow")
            return 0
        
        self.rsp -= 1
        return self.return_stack[self.rsp]
    
    # Word handling
    def find_word(self, name):
        """Find a word in the dictionary by name"""
        # Search from newest to oldest
        for i in range(len(self.dictionary) - 1, -1, -1):
            if self.dictionary[i][0].upper() == name.upper():
                return i
        return -1  # Word not found
    
    def add_primitive(self, name, func, immediate=False):
        """Add a primitive (built-in) word to the dictionary"""
        if len(self.dictionary) >= self.DICT_SIZE:
            self._error("Dictionary full")
            return
        
        self.dictionary.append((name, immediate, func, True))
    
    def create_word(self, name):
        """Create a new user-defined word"""
        if len(self.dictionary) >= self.DICT_SIZE:
            self._error("Dictionary full")
            return -1
        
        # Start address in code space
        code_ptr = self.code_idx
        # Add to dictionary: (name, immediate flag, code_ptr, is_primitive=False)
        self.dictionary.append((name, False, code_ptr, False))
        return len(self.dictionary) - 1
    
    def add_to_definition(self, value):
        """Add a value to the current word definition"""
        if self.code_idx >= self.MAX_CODE_SIZE:
            self._error("Code space full")
            return
        
        self.code_space[self.code_idx] = value
        self.code_idx += 1
    
    # Parser
    def parse_word(self):
        """Parse the next word from the input buffer"""
        # Skip whitespace
        while self.input_pos < len(self.input_buffer) and self.input_buffer[self.input_pos].isspace():
            self.input_pos += 1
        
        if self.input_pos >= len(self.input_buffer):
            return None  # End of input
        
        # Parse the word
        start = self.input_pos
        while (self.input_pos < len(self.input_buffer) and 
               not self.input_buffer[self.input_pos].isspace()):
            self.input_pos += 1
        
        if start == self.input_pos:
            return None
        
        return self.input_buffer[start:self.input_pos]
    
    def is_number(self, s):
        """Check if a string is a valid number"""
        if not s:
            return False
        
        # Handle hexadecimal
        if s.startswith('0x') or s.startswith('0X'):
            try:
                int(s, 16)
                return True
            except ValueError:
                return False
        
        # Regular decimal
        try:
            int(s)
            return True
        except ValueError:
            return False
    
    def parse_number(self, s):
        """Parse a number from a string, handling 16-bit constraints"""
        try:
            # Handle hexadecimal
            if s.startswith('0x') or s.startswith('0X'):
                value = int(s, 16)
            else:
                value = int(s)
            
            # Clamp to 16-bit signed range
            if value > 32767:
                value = 32767
            elif value < -32768:
                value = -32768
            
            return value
        except ValueError:
            self._error(f"Invalid number: {s}")
            return 0
    
    # Execution
    def execute(self, word_idx):
        """Execute a word by its dictionary index"""
        if word_idx < 0 or word_idx >= len(self.dictionary):
            self._error("Invalid word index")
            return
        
        word = self.dictionary[word_idx]
        name, immediate, code_ptr, is_primitive = word
        
        if is_primitive:
            # Execute primitive (built-in) word
            func = code_ptr
            func(self)
        else:
            # Execute user-defined word
            # Save previous position for nested calls
            prev_pos = None
            
            # Interpret the code
            i = code_ptr
            while i < self.code_idx and self.running:
                instr = self.code_space[i]
                i += 1
                
                if isinstance(instr, int):
                    if instr >= 0:
                        if instr == self.find_word("0BRANCH"):
                            # This is a conditional branch instruction
                            # Pop the condition from the stack
                            condition = self.pop()
                            
                            # If condition is false (0), branch to the target address
                            if condition == 0:
                                i = self.code_space[i]
                            else:
                                # Skip the branch target
                                i += 1
                        elif instr == self.find_word("BRANCH"):
                            # Unconditional branch
                            i = self.code_space[i]
                        else:
                            # Word reference - execute it
                            self.execute(instr)
                    else:
                        # Literal value - push to stack
                        self.push(-instr - 1)
            
    def interpret(self, input_str):
        """Interpret a line of FORTH code"""
        self.input_buffer = input_str
        self.input_pos = 0
        
        word = self.parse_word()
        while word and self.running:
            word_idx = self.find_word(word)
            
            if word_idx >= 0:
                word_entry = self.dictionary[word_idx]
                if self.compiling and not word_entry[1]:  # Not immediate
                    # Add word reference to current definition
                    self.add_to_definition(word_idx)
                else:
                    # Execute the word
                    self.execute(word_idx)
            elif self.is_number(word):
                # Handle numbers
                num = self.parse_number(word)
                
                if self.compiling:
                    # Add literal to current definition
                    # Store as negative to distinguish from word references
                    self.add_to_definition(-num - 1)
                else:
                    # Push to stack
                    self.push(num)
            else:
                self._error(f"Unknown word: {word}")
                break
            
            word = self.parse_word()
    
    # Error handling
    def _error(self, message):
        """Handle errors"""
        self.last_error = message
        print(f"Error: {message}")
        # Don't halt execution on error in interpreter mode
        if self.compiling:
            self.running = False
    
    # Initialize built-in words
    def _init_primitives(self):
        """Initialize built-in words"""
        # Stack manipulation
        self.add_primitive("DUP", lambda vm: vm.push(vm.stack[vm.sp-1] if vm.sp > 0 else vm._error("Stack underflow")))
        self.add_primitive("DROP", lambda vm: vm.pop())
        self.add_primitive("SWAP", lambda vm: vm._swap())
        self.add_primitive("OVER", lambda vm: vm._over())
        self.add_primitive("ROT", lambda vm: vm._rot())
        
        # Return stack
        self.add_primitive(">R", lambda vm: vm.rpush(vm.pop()))
        self.add_primitive("R>", lambda vm: vm.push(vm.rpop()))
        self.add_primitive("R@", lambda vm: vm.push(vm.return_stack[vm.rsp-1] if vm.rsp > 0 else vm._error("Return stack underflow")))
        
        # Arithmetic
        self.add_primitive("+", lambda vm: vm.push(vm.pop() + vm.pop() if vm.sp >= 2 else vm._error("Stack underflow")))
        self.add_primitive("-", lambda vm: vm._sub())
        self.add_primitive("*", lambda vm: vm.push(vm.pop() * vm.pop() if vm.sp >= 2 else vm._error("Stack underflow")))
        self.add_primitive("/", lambda vm: vm._div())
        self.add_primitive("MOD", lambda vm: vm._mod())
        
        # Logic
        self.add_primitive("AND", lambda vm: vm.push(vm.pop() & vm.pop()))
        self.add_primitive("OR", lambda vm: vm.push(vm.pop() | vm.pop()))
        self.add_primitive("XOR", lambda vm: vm.push(vm.pop() ^ vm.pop()))
        self.add_primitive("NOT", lambda vm: vm.push(~vm.pop() & 0xFFFF))
        
        # Comparison
        self.add_primitive("=", lambda vm: vm._equals())
        self.add_primitive("<>", lambda vm: vm._not_equals())
        self.add_primitive("<", lambda vm: vm._less_than())
        self.add_primitive(">", lambda vm: vm._greater_than())
        self.add_primitive("<=", lambda vm: vm._less_equal())
        self.add_primitive(">=", lambda vm: vm._greater_equal())
        
        # I/O
        self.add_primitive("EMIT", lambda vm: vm._emit())
        self.add_primitive("CR", lambda vm: print())
        self.add_primitive(".", lambda vm: vm._dot())
        self.add_primitive(".S", lambda vm: vm._dot_s())
        
        # Defining words
        self.add_primitive(":", lambda vm: vm._colon())
        self.add_primitive(";", lambda vm: vm._semicolon(), immediate=True)
        self.add_primitive("EXIT", lambda vm: vm._exit())
        
        # Control structures
        self.add_primitive("0BRANCH", lambda vm: None)  # Special instruction handled in execute
        self.add_primitive("BRANCH", lambda vm: None)   # Special instruction for unconditional branch
        self.add_primitive("IF", lambda vm: vm._if(), immediate=True)
        self.add_primitive("ELSE", lambda vm: vm._else(), immediate=True)
        self.add_primitive("THEN", lambda vm: vm._then(), immediate=True)
        self.add_primitive("DO", lambda vm: vm._do(), immediate=True)
        self.add_primitive("LOOP", lambda vm: vm._loop(), immediate=True)
        self.add_primitive("I", lambda vm: vm._i())
        self.add_primitive("J", lambda vm: vm._j())
        
        # String literals
        self.add_primitive('."', lambda vm: vm._dot_quote(), immediate=True)
        self.add_primitive('(")', lambda vm: vm._print_string())  # Runtime routine for ."
    
    # Implementation of primitive words
    def _swap(self):
        if self.sp < 2:
            self._error("Stack underflow")
            return
        self.stack[self.sp - 1], self.stack[self.sp - 2] = self.stack[self.sp - 2], self.stack[self.sp - 1]
    
    def _over(self):
        if self.sp < 2:
            self._error("Stack underflow")
            return
        self.push(self.stack[self.sp - 2])
    
    def _rot(self):
        if self.sp < 3:
            self._error("Stack underflow")
            return
        
        a = self.stack[self.sp - 3]
        self.stack[self.sp - 3] = self.stack[self.sp - 2]
        self.stack[self.sp - 2] = self.stack[self.sp - 1]
        self.stack[self.sp - 1] = a
    
    def _sub(self):
        if self.sp < 2:
            self._error("Stack underflow")
            return
        b = self.pop()
        a = self.pop()
        self.push(a - b)
    
    def _div(self):
        if self.sp < 2:
            self._error("Stack underflow")
            return
        b = self.pop()
        if b == 0:
            self._error("Division by zero")
            self.push(0)
            return
        a = self.pop()
        self.push(a // b)  # Integer division
    
    def _mod(self):
        if self.sp < 2:
            self._error("Stack underflow")
            return
        b = self.pop()
        if b == 0:
            self._error("Division by zero")
            self.push(0)
            return
        a = self.pop()
        self.push(a % b)
    
    def _equals(self):
        if self.sp < 2:
            self._error("Stack underflow")
            return
        b = self.pop()
        a = self.pop()
        self.push(-1 if a == b else 0)  # -1 is true in FORTH
    
    def _not_equals(self):
        if self.sp < 2:
            self._error("Stack underflow")
            return
        b = self.pop()
        a = self.pop()
        self.push(-1 if a != b else 0)
    
    def _less_than(self):
        if self.sp < 2:
            self._error("Stack underflow")
            return
        b = self.pop()
        a = self.pop()
        self.push(-1 if a < b else 0)
    
    def _greater_than(self):
        if self.sp < 2:
            self._error("Stack underflow")
            return
        b = self.pop()
        a = self.pop()
        self.push(-1 if a > b else 0)
    
    def _less_equal(self):
        if self.sp < 2:
            self._error("Stack underflow")
            return
        b = self.pop()
        a = self.pop()
        self.push(-1 if a <= b else 0)
    
    def _greater_equal(self):
        if self.sp < 2:
            self._error("Stack underflow")
            return
        b = self.pop()
        a = self.pop()
        self.push(-1 if a >= b else 0)
    
    def _emit(self):
        if self.sp < 1:
            self._error("Stack underflow")
            return
        char = self.pop()
        print(chr(char), end='')
    
    def _dot(self):
        if self.sp < 1:
            self._error("Stack underflow")
            return
        value = self.pop()
        print(value, end=' ')
    
    def _dot_s(self):
        print("[ ", end='')
        for i in range(self.sp):
            print(self.stack[i], end=' ')
        print("]", end='')
    
    def _colon(self):
        word = self.parse_word()
        if not word:
            self._error("Expected word name after ':'")
            return
        
        self.current_word = self.create_word(word)
        self.compiling = True
    
    def _semicolon(self):
        if not self.compiling:
            self._error("';' outside of definition")
            return
        
        # Add EXIT to end of definition
        exit_idx = self.find_word("EXIT")
        if exit_idx >= 0:
            self.add_to_definition(exit_idx)
        
        self.compiling = False
    
    def _exit(self):
        # Not needed in this Python implementation
        pass
    
    def _if(self):
        if not self.compiling:
            self._error("'IF' outside of definition")
            return
        
        # Add 0BRANCH instruction
        branch_instr = self.find_word("0BRANCH")
        if branch_instr < 0:
            self._error("0BRANCH word not found")
            return
            
        self.add_to_definition(branch_instr)
        
        # Add placeholder for branch offset
        branch_idx = self.code_idx
        self.add_to_definition(None)  # Will fill in later
        
        # Push branch location to return stack for later resolution
        self.rpush(branch_idx)
    
    def _else(self):
        if not self.compiling:
            self._error("'ELSE' outside of definition")
            return
        
        # Get IF branch location
        if_branch_idx = self.rpop()
        
        # Add unconditional branch to skip ELSE part
        branch_instr = self.find_word("BRANCH")
        if branch_instr < 0:
            self._error("BRANCH word not found")
            return
            
        self.add_to_definition(branch_instr)
        
        # Add placeholder for branch offset
        else_branch_idx = self.code_idx
        self.add_to_definition(None)  # Will fill in later
        
        # Fill in the IF branch target (to jump to after ELSE)
        self.code_space[if_branch_idx] = self.code_idx
        
        # Push ELSE branch for THEN to resolve
        self.rpush(else_branch_idx)
    
    def _then(self):
        if not self.compiling:
            self._error("'THEN' outside of definition")
            return
        
        # Get branch location (from IF or ELSE)
        branch_idx = self.rpop()
        
        # Fill in the branch target
        self.code_space[branch_idx] = self.code_idx
    
    def _do(self):
        if not self.compiling:
            self._error("'DO' outside of definition")
            return
        
        # Push loop start location
        self.rpush(self.code_idx)
    
    def _loop(self):
        if not self.compiling:
            self._error("'LOOP' outside of definition")
            return
        
        # Get loop start location
        start_idx = self.rpop()
        
        # Add branch back to start of loop
        self.add_to_definition(start_idx)
    
    def _i(self):
        if self.rsp < 1:
            self._error("Return stack underflow")
            return
        
        # Access loop index
        self.push(self.return_stack[self.rsp - 1])
    
    def _j(self):
        if self.rsp < 3:
            self._error("Return stack underflow")
            return
        
        # Access outer loop index
        self.push(self.return_stack[self.rsp - 3])
    
    def _dot_quote(self):
        """Compile a string literal for printing"""
        if not self.compiling:
            # Skip the space after ."
            if self.input_pos < len(self.input_buffer) and self.input_buffer[self.input_pos].isspace():
                self.input_pos += 1
            
            # Find the closing quote
            start = self.input_pos
            while self.input_pos < len(self.input_buffer) and self.input_buffer[self.input_pos] != '"':
                self.input_pos += 1
            
            if self.input_pos >= len(self.input_buffer):
                self._error("Unterminated string")
                return
            
            # Extract and print the string
            string = self.input_buffer[start:self.input_pos]
            print(string, end='')
            
            # Skip the closing quote
            self.input_pos += 1
            return
        
        # Compile-time behavior
        # Skip the space after ."
        if self.input_pos < len(self.input_buffer) and self.input_buffer[self.input_pos].isspace():
            self.input_pos += 1
        
        # Find the closing quote
        start = self.input_pos
        while self.input_pos < len(self.input_buffer) and self.input_buffer[self.input_pos] != '"':
            self.input_pos += 1
        
        if self.input_pos >= len(self.input_buffer):
            self._error("Unterminated string")
            return
        
        # Extract the string
        string = self.input_buffer[start:self.input_pos]
        
        # Skip the closing quote
        self.input_pos += 1
        
        # In this VM implementation, we'll use a different approach
        # We'll compile code to push each character and call EMIT
        # This is less efficient but works with the existing VM architecture
        emit_idx = self.find_word("EMIT")
        if emit_idx < 0:
            self._error("EMIT word not found")
            return
        
        for char in string:
            # Add code to push character and emit it
            self.add_to_definition(-ord(char) - 1)  # Push character as literal
            self.add_to_definition(emit_idx)
    
    def _print_string(self):
        """Runtime routine for printing strings - not used in this implementation"""
        # This method is not used in the current implementation
        # We're using a series of character literals and EMIT calls instead
        pass


# Entry point for Pico application
def main():
    """Main FORTH interpreter loop"""
    forth = ForthVM()
    
    print("MicroPython FORTH VM for Raspberry Pi Pico")
    print("Enter FORTH commands, 'bye' to exit")
    
    try:
        while forth.running:
            try:
                input_line = input("> ")
                if input_line.lower() == "bye":
                    break
                forth.interpret(input_line)
            except Exception as e:
                print(f"Internal error: {e}")
    except KeyboardInterrupt:
        print("\nExiting FORTH VM")
    
    print("Goodbye!")


# Pico-specific initialization
if __name__ == "__main__":
    # Uncomment these lines when running on Pico with MicroPython
    import machine
    import utime
    
    # Run the FORTH VM
    main()
