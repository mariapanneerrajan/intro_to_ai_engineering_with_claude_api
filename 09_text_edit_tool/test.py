import sys
from main import calculate_pi


def test_calculate_pi():
    """
    Test the calculate_pi function to verify it returns pi to the 5th digit.
    Pi to the 5th digit is: 3.14159
    """
    result = calculate_pi()
    
    print(f"Calculated pi: {result}")
    print(f"Calculated pi (to 5 decimals): {result:.5f}")
    
    # Expected value of pi to the 5th digit
    expected = 3.14159
    
    # Check if the result matches to the 5th digit
    result_rounded = round(result, 5)
    
    print(f"\nExpected pi (to 5 decimals): {expected}")
    print(f"Result rounded to 5 decimals: {result_rounded}")
    
    # Verify the result
    if result_rounded == expected:
        print("\n✓ Test PASSED! Pi calculated correctly to the 5th digit.")
        return True
    else:
        print("\n✗ Test FAILED! Result does not match expected value.")
        return False


if __name__ == "__main__":
    success = test_calculate_pi()
    sys.exit(0 if success else 1)
