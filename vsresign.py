#!/usr/bin/env python
# -*- coding: utf-8 -*-

# to run this scipt make sure you installed python module biplist
# sudo easy_install biplist


import os
import fnmatch
import argparse
import plistlib
import biplist
import sys
import subprocess
import zipfile
import shutil
import datetime
import codecs
import pprint
import ast
from ConfigParser import SafeConfigParser

sys.path.append("lib")

tmpdir = "tmp"                           # temp directory for extraction / repack
executable_file = "Visionaire Player"    # pre-defined executable to find


def which(application):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(application)
    if fpath:
        if is_exe(application):
            return application
    return None


def get_platform(platform):
    if platform.endswith('.ipa'):
        result = "iOS"
    elif platform.endswith('.zip'):
        result = "MacOS"
    else:
        result = None
    return result


def rename(executable_in, executable_out):
    executable_out = os.path.dirname(os.path.relpath(executable_in)) + '/' + executable_out
    print "~ rename : ", executable_in, ' -> ', executable_out
    os.rename(executable_in, executable_out)
    return executable_out


def unzip(application, directory):
    with zipfile.ZipFile(application, "r") as z:
        z.extractall(directory)


def zip(src, dst, ext):
    print ("~ compress target")
    zf = zipfile.ZipFile("%s" % (dst+ext), "w", zipfile.ZIP_DEFLATED)
    abs_src = os.path.abspath(src)
    for dirname, subdirs, files in os.walk(src):
        for filename in files:
            absname = os.path.abspath(os.path.join(dirname, filename))
            arcname = absname[len(abs_src) + 1:]
            zf.write(absname, arcname)
    zf.close()
    print ("~ compress done")


def cleanupdirectory(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)


def stringreplace(string):
    #if isinstance(string, unicode):
    #    string = string.encode("utf-8")
    if '{YEAR}' in string:
        string = string.replace('{YEAR}', datetime.date.today().strftime("%Y"))
    if '{COPYRIGHT SIGN}' in string:
        string = string.replace('{COPYRIGHT SIGN}', u'\N{COPYRIGHT SIGN}'.encode('utf-8'))
    try:
        string = ast.literal_eval(string)
    except Exception:
        string = ast.literal_eval('"%s"' % string)
    return string


#def find(name, path):
#    for root, dirs, files in os.walk(path):
#        if name in files:
#            return os.path.join(root, name)
#        if name in dirs:
#            return os.path.join(root, name)

def find(pattern, path):
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                return os.path.join(root, name)
        for name in dirs:
            if fnmatch.fnmatch(name, pattern):
                return os.path.join(root, name)


if not which("/usr/bin/codesign"):
    print("Error: codesign binary not found. Install XCode and commandline tools.")
if not which("/usr/bin/unzip"):
    print("Error: unzip not found. Cannot run without the unzip utility present at /usr/bin/unzip")
if not which("/usr/bin/zip"):
    print("Error: zip not found. Cannot run without the zip utility present at /usr/bin/zip")
if not which("/usr/bin/sips"):
    print("Error: sips not found. Cannot run without the sips utility present at /usr/bin/sips")


parser = argparse.ArgumentParser(description='Visionaire-Studio resign tool')

parser.add_argument('-l', '--list',
                    help="list available signing certificates",
                    action='store_true')

parser.add_argument('-c',
                    default=False,
                    dest="config_file",
                    metavar="FILE",
                    help="specify config file")

parser.add_argument('-i',
                    default=False,
                    dest="input_file",
                    metavar="FILE",
                    help="specify target input file")

args = parser.parse_args()
if args.config_file is False or args.input_file is False:
    if args.list:
        print("~ List: {}".format(args.list))
        sys.exit(subprocess.call(["security", "find-identity", "-p", "codesigning", '-v']))
    sys.exit(parser.print_help())


platform = get_platform(args.input_file)
if platform is None:
    sys.exit('Error: unsupported player file')

input_file = args.input_file
config_file = args.config_file


print("~ INPUT : {}".format(input_file))
print("~ INPUT Platform : {}".format(input_file))
print("~ INPUT Config: {}".format(config_file))

if not os.path.isfile(input_file):
    sys.exit('INPUT file does not exist: {}'.format(input_file))
if not os.path.isfile(config_file):
    sys.exit('CONFIG file does not exist: {}'.format(config_file))

print("~ Cleanup tmp directory")
cleanupdirectory(tmpdir)


unzip(input_file, tmpdir)
application_path = find("*.app", tmpdir)


parser = SafeConfigParser()
parser.optionxform=str
parser.read(config_file)
plist_file = find('Info.plist', application_path)
executable_file = find(executable_file, application_path)

plist = biplist.readPlist(plist_file)

for section_name in parser.sections():
    print '~~ Section:', section_name
    certificate = parser.get(section_name, 'certificate')
    plist_overwrite = parser.getboolean(section_name, 'info_plist_overwrite')
    entitlement_overwrite = parser.getboolean(section_name, 'entitlement_overwrite')
    generate_pkg = parser.getboolean(section_name, 'generate_macappstore_pkg')
    if parser.has_option(section_name, 'CFBundleExecutable'):
        executable_name = parser.get(section_name, 'CFBundleExecutable')
        print '~~~~ set: CFBundleExecutable ->', executable_name
    if parser.has_option(section_name, 'CFBundleName'):
        application_name = parser.get(section_name, 'CFBundleName')
        print '~~~~ set: CFBundleName ->', application_name

    if not certificate:
        sys.exit('Error: No certificate')

    #plist
    if plist_overwrite:
        print '~~~ Generate plist:', section_name
        for name, value in parser.items(section_name):
            if name.startswith('info_plist_'):
                line = name.replace('info_plist_', '')
                if not 'icon' in line and not 'overwrite' in line:
                    #replace functions
                    value = stringreplace(value)
                    if not value:
                        del plist[line]
                        print '~~~~ del:', line
                    else:
                        plist[line] = value
                        print '~~~~ set:', line, '->', value
                    if 'CFBundleExecutable' in line:
                        executable_name = value
                    if 'CFBundleName' in line:
                        application_name = value
        biplist.writePlist(plist, plist_file)
    else:
        print '~~~ Skip generate plist:', section_name

    #entitlements
    if entitlement_overwrite:
        entitlement = {}
        print '~~~ Generate entitlements:', section_name
        for name, value in parser.items(section_name):
            if name.startswith('entitlement_'):
                line = name.replace('entitlement_', '')
                if not 'overwrite' in line:
                    print '~~~~ set:', line, '->', value
                    if 'app-sandbox' in line:
                        entitlement.update({'com.apple.security.app-sandbox': True})
        plistlib.writePlist(entitlement, tmpdir + '/entitlement.plist')
    else:
        print '~~~ Skip generate entitlement:', section_name

    # generic
    shutil.rmtree(find('_CodeSignature', tmpdir))
    # platform iOS
    if platform is "iOS":
        rename(executable_file, executable_name)
        application_path = rename(application_path, application_name + '.app')
        mobile_provisioning_profile = parser.get(section_name, 'ios_embedded.mobileprovision')
        if mobile_provisioning_profile:
            os.remove(find('embedded.mobileprovision', tmpdir))
            shutil.copyfile(mobile_provisioning_profile, application_path+'/embedded.mobileprovision')
        else:
            sys.exit("Error: need ios_embedded.mobileprovision profile")
        cmd = ["codesign", "--sign", certificate, "--force", '--verbose']
        if entitlement_overwrite:
            cmd = cmd + ["--entitlements="+find("entitlement.plist", tmpdir)]
        cmd = cmd + [application_path]
        subprocess.call(cmd)
        zip('tmp', "./" + section_name, '.ipa')
    # platform MacOS
    if platform is "MacOS":
        sys.exit("coming soon…")
        cmd = ["codesign", "--deep", "--sign", certificate, "--force", '--verbose']
        if entitlement_overwrite:
            cmd = cmd + ["--entitlements="+find("entitlement.plist", tmpdir)]
        cmd = cmd + [application_path]
        subprocess.call(cmd)
        zip('tmp', "./" + section_name, '.zip')


print("~ Cleanup tmp directory")
cleanupdirectory(tmpdir)



