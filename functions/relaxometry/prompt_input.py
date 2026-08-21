def prompt_input(prompt, n_min, n_max):
    while True:
        try:
            answer = int(input(prompt))
        except ValueError:
            print("Error: Enter a number from range", n_min,"to",n_max)
        else:
            if answer in range(n_min,n_max+1):
                break
            else:
                print("Error: Enter a number from range", n_min,"to",n_max)
    return answer