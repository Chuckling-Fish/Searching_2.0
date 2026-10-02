#include <iostream>

int addNumbers(int a, int b) {
    return a + b;
}

class Calculator {
public:
    int multiply(int a, int b) {
        return a * b;
    }
};
int sumEven(int n) {
    int total = 0;

    for (int i = 0; i < n; i++) {
        if (i % 2 == 0) {
            total += i;
        }
    }

    return total;
}