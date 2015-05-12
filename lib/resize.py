import os
import sys
import commands


def getHeightWidth(file):
    widthstr = commands.getstatusoutput('sips -g pixelWidth {0}'.format(file))[1]
    heightstr = commands.getstatusoutput('sips -g pixelHeight {0}'.format(file))[1]
    width = int(widthstr.split('pixelWidth: ')[1])
    height = int(heightstr.split('pixelHeight: ')[1])

    return height, width


def resize(file, height, width, target_height, target_width):
    if height <= width:
        commands.getstatusoutput('sips -z {0} {1} {2}'.format(min(target_width, target_height), max(target_width, target_height), file))
    else:
        commands.getstatusoutput('sips -z {0} {1} {2}'.format(max(target_width, target_height), min(target_width, target_height), file))


def main(args):
    if len(args) == 3:
        target_height = int(args[0])
        target_width = int(args[1])

        for f in os.listdir(args[2]):
            if 'jpg' in f.lower() or 'png' in f.lower():
                f = args[2] + '/' + f
                height, width = getHeightWidth(f)
                resize(f, height, width, target_height, target_width)


if __name__ == '__main__':
    main(sys.argv[1:])