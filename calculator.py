def main():
    try:
        num1 = float(input("Enter the first number: "))
    except ValueError:
        print("Invalid input for the first number.")
        return

    try:
        num2 = float(input("Enter the second number: "))
    except ValueError:
        print("Invalid input for the second number.")
        return

    op = input("Enter an operation (+, -, *, /): ").strip()

    if op not in ('+', '-', '*', '/'):
        print("Invalid operation. Please choose +, -, *, or /.")
        return

    if op == '+':
        result = num1 + num2
    elif op == '-':
        result = num1 - num2
    elif op == '*':
        result = num1 * num2
    elif op == '/':
        if num2 == 0:
            print("Error: Division by zero is not allowed.")
            return
        result = num1 / num2

    print(f"The result is: {result}")

if __name__ == "__main__":
    main()