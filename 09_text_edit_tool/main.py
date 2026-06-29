def greeting():
    print("Hi there!")


def calculate_pi():
    """
    Calculate pi to the 5th digit using the Machin formula.
    Returns pi approximately as 3.14159
    """
    from decimal import Decimal, getcontext
    
    # Set precision to 10 decimal places to ensure accuracy to the 5th digit
    getcontext().prec = 10
    
    # Using the Machin formula: pi/4 = 4*arctan(1/5) - arctan(1/239)
    # This converges quickly and gives us good precision
    
    one = Decimal(1)
    five = Decimal(5)
    two_three_nine = Decimal(239)
    
    # Calculate arctan using Taylor series
    def arctan(x, num_terms=50):
        power = x
        result = power
        for n in range(1, num_terms):
            power *= -x * x
            result += power / (2 * n + 1)
        return result
    
    pi = 4 * (4 * arctan(one / five) - arctan(one / two_three_nine))
    
    return float(pi)
