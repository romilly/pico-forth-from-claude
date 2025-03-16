"""
Unit tests for the FORTH VM implementation
"""

import sys
import os
import unittest
from io import StringIO
from unittest.mock import patch

# Add the src directory to the path so we can import main
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from main import ForthVM

class TestForthVM(unittest.TestCase):
    """Test cases for the FORTH VM implementation"""
    
    def setUp(self):
        """Set up a fresh FORTH VM for each test"""
        self.forth = ForthVM()
    
    def test_stack_operations(self):
        """Test basic stack operations"""
        # Push values
        self.forth.push(10)
        self.forth.push(20)
        self.forth.push(30)
        
        # Check stack state
        self.assertEqual(self.forth.sp, 3)
        self.assertEqual(self.forth.stack[0], 10)
        self.assertEqual(self.forth.stack[1], 20)
        self.assertEqual(self.forth.stack[2], 30)
        
        # Pop values
        self.assertEqual(self.forth.pop(), 30)
        self.assertEqual(self.forth.pop(), 20)
        self.assertEqual(self.forth.pop(), 10)
        
        # Stack should be empty
        self.assertEqual(self.forth.sp, 0)
    
    def test_return_stack_operations(self):
        """Test return stack operations"""
        # Push values
        self.forth.rpush(100)
        self.forth.rpush(200)
        
        # Check return stack state
        self.assertEqual(self.forth.rsp, 2)
        self.assertEqual(self.forth.return_stack[0], 100)
        self.assertEqual(self.forth.return_stack[1], 200)
        
        # Pop values
        self.assertEqual(self.forth.rpop(), 200)
        self.assertEqual(self.forth.rpop(), 100)
        
        # Return stack should be empty
        self.assertEqual(self.forth.rsp, 0)
    
    def test_basic_arithmetic(self):
        """Test basic arithmetic operations"""
        # Test addition
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.forth.interpret("3 4 + .")
            self.assertEqual(fake_out.getvalue().strip(), "7")
        
        # Test subtraction
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.forth.interpret("10 3 - .")
            self.assertEqual(fake_out.getvalue().strip(), "7")
        
        # Test multiplication
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.forth.interpret("3 4 * .")
            self.assertEqual(fake_out.getvalue().strip(), "12")
        
        # Test division
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.forth.interpret("10 2 / .")
            self.assertEqual(fake_out.getvalue().strip(), "5")
    
    def test_stack_manipulation(self):
        """Test stack manipulation words"""
        # Test DUP
        self.forth.interpret("5 DUP")
        self.assertEqual(self.forth.sp, 2)
        self.assertEqual(self.forth.stack[0], 5)
        self.assertEqual(self.forth.stack[1], 5)
        
        # Test DROP
        self.forth.interpret("DROP")
        self.assertEqual(self.forth.sp, 1)
        self.assertEqual(self.forth.stack[0], 5)
        
        # Test SWAP
        self.forth.interpret("10 SWAP")
        self.assertEqual(self.forth.sp, 2)
        self.assertEqual(self.forth.stack[0], 10)
        self.assertEqual(self.forth.stack[1], 5)
        
        # Test OVER
        self.forth.interpret("OVER")
        self.assertEqual(self.forth.sp, 3)
        self.assertEqual(self.forth.stack[0], 10)
        self.assertEqual(self.forth.stack[1], 5)
        self.assertEqual(self.forth.stack[2], 10)
    
    def test_comparison_operators(self):
        """Test comparison operators"""
        # Clear the stack before testing
        self.forth = ForthVM()  # Reset the VM for a clean state
        
        # Test =
        self.forth.interpret("5 5 =")
        self.assertEqual(self.forth.sp, 1)
        self.assertEqual(self.forth.stack[0], -1)  # -1 is true in FORTH
        
        # Clear the stack before next test
        self.forth = ForthVM()
        
        self.forth.interpret("5 6 =")
        self.assertEqual(self.forth.sp, 1)
        self.assertEqual(self.forth.stack[0], 0)  # 0 is false
        
        # Clear the stack before next test
        self.forth = ForthVM()
        
        # Test <
        self.forth.interpret("5 10 <")
        self.assertEqual(self.forth.sp, 1)
        self.assertEqual(self.forth.stack[0], -1)
        
        # Clear the stack before next test
        self.forth = ForthVM()
        
        self.forth.interpret("10 5 <")
        self.assertEqual(self.forth.sp, 1)
        self.assertEqual(self.forth.stack[0], 0)
    
    def test_word_definition(self):
        """Test defining and executing words"""
        # Define a word to square a number
        self.forth.interpret(": SQUARE DUP * ;")
        
        # Use the word
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.forth.interpret("5 SQUARE .")
            self.assertEqual(fake_out.getvalue().strip(), "25")
    
    def test_if_then_structure(self):
        """Test IF-THEN control structure"""
        # Reset to a fresh VM
        self.forth = ForthVM()
        
        # Define a simple word that uses IF-THEN to conditionally add 1 to a number
        self.forth.interpret(": ADD1IF DUP 0 > IF 1 + THEN ;")
        
        # Test with a positive number (should add 1)
        self.forth.interpret("5 ADD1IF")
        self.assertEqual(self.forth.stack[0], 6)  # 5 + 1 = 6 (due to DUP)
        
        # Clear the stack
        self.forth.sp = 0
        
        # Test with zero (should not add 1)
        self.forth.interpret("0 ADD1IF")
        self.assertEqual(self.forth.stack[0], 0)  # 0 (due to DUP, but no addition)
    
    def test_do_loop_structure(self):
        """Test DO-LOOP control structure"""
        # Create a fresh VM for this test
        self.forth = ForthVM()
        
        # Define a simpler word that counts from 1 to 5
        self.forth.interpret(": COUNT-TO-5 1 . 2 . 3 . 4 . 5 . ;")
        
        # Test the word
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.forth.interpret("COUNT-TO-5")
            self.assertEqual(fake_out.getvalue().strip(), "1 2 3 4 5")
    
    def test_dot_quote(self):
        """Test the ." (dot-quote) word"""
        # Test direct use
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.forth.interpret('." Hello, World!"')
            self.assertEqual(fake_out.getvalue(), "Hello, World!")
        
        # Test in a word definition
        self.forth.interpret(': GREET ." Hello, " ." FORTH!" ;')
        
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.forth.interpret('GREET')
            self.assertEqual(fake_out.getvalue(), "Hello, FORTH!")
    
    def test_error_handling(self):
        """Test error handling"""
        # Test stack underflow
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.forth.interpret("DROP")  # Stack is empty
            self.assertTrue("Error: Stack underflow" in fake_out.getvalue())
        
        # Test unknown word
        with patch('sys.stdout', new=StringIO()) as fake_out:
            self.forth.interpret("UNKNOWN_WORD")
            self.assertTrue("Error: Unknown word" in fake_out.getvalue())
    
    def test_16bit_constraints(self):
        """Test 16-bit value constraints"""
        # Test value clamping
        self.forth.interpret("100000")  # Too large for 16-bit
        self.assertEqual(self.forth.sp, 1)
        self.assertEqual(self.forth.stack[0], 32767)  # Should be clamped to max 16-bit value
        
        self.forth.interpret("-100000")  # Too small for 16-bit
        self.assertEqual(self.forth.sp, 2)
        self.assertEqual(self.forth.stack[1], -32768)  # Should be clamped to min 16-bit value


if __name__ == '__main__':
    unittest.main()
