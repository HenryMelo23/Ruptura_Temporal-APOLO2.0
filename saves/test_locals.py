def f():
    for i in range(10):
        if i >= 5:
            if 'x' not in locals():
                x = 10
                print("x initialized")
            print(f"x = {x}")
f()
