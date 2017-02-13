import sys


def myprogressbar(batchsize, totalsize, barlength=25, message='', char="#"):
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
