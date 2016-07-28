import sys


def myprogressbar(batchsize, totalsize, barlength=25, message='', char="#"):
    '''
    creates a custom progress bar

    :param batchsize: number of items to process
    :param totalsize: total size of all items to process
    :param barlength: number symbols to show (default = 25)
    :param message: custom message (default = '')
    :param char: character to visualize (default = '#')
    :return:
    '''
    addtooutput = cmdorgui()
    percent = batchsize / float(totalsize)
    chars = char * int(round(percent * barlength))
    spaces = " " * (barlength - len(chars))
    output = '\r' + message + '[{0}] {1:.1f}% ({2}/{3})'.format(chars + spaces,
                                                                round(percent * 100, 2),
                                                                batchsize,
                                                                totalsize) + addtooutput
    sys.stdout.write(output)
    sys.stdout.flush()


def cmdorgui():
    '''
    figures out if the .py program is running in the exe window or IDEL
    interface

    :return: new line or ''
    '''

    a = sys.executable
    m = '\\'
    m = m[0]
    while True:
        b = len(a)
        c = a[(b - 1)]
        if c == m:
            break
        a = a[:(b - 1)]
    if sys.executable == a + 'pythonw.exe':
        # Running in IDLE GUI interface
        return '\n'
    else:
        # Running from the command line
        return ''

# example
# import time
# x=20
# for i in range(x):
#   myprogressbar(i,x,barlength=10,message='Test P_Bar:',char='.')
#   time.sleep(.1)
