class A:
    @staticmethod
    def get_func():
        state = 0
        def stateful_method():
            nonlocal state
            state += 1
            return state
        return stateful_method



def func1(idx):
    func = A.get_func()
    print(func())
    print(func())

def func2(idx):
    func = A.get_func()
    print(func())
    print(func())
    print(func())



func2(0)
func1(0)
