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
from ConfigParser import SafeConfigParser

import pprint

sys.path.append("lib")

tmpdir = "tmp"

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
    result = ''
    if '{YEAR}' in string:
        string = string.replace('{YEAR}', datetime.date.today().strftime("%Y"))
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
                    action="store_true",
                    help="list available signing certificates")

parser.add_argument('config_file',
                    #dest='config_filename',
                    #required=True,
                    #metavar="CONFIG_FILE",
                    help="specify config file")

parser.add_argument('target',
                    action="store",
                    help="Codesign target")

args = parser.parse_args()

print("~ List: {}".format(args.list))
if args.list:
    subprocess.call(["security", "find-identity", "-p", "codesigning", '-v'])
    exit()

platform = get_platform(args.target)
if platform is None:
    print('Error: unsupported player file')
    exit(1)

target = args.target
config_file = args.config_file


print("~ Target : {}".format(target))
print("~ Target Platform : {}".format(platform))
print("~ Target Config: {}".format(config_file))


print("~ Cleanup tmp directory")
cleanupdirectory(tmpdir)


unzip(target, tmpdir)
application_path = find("*.app", tmpdir)


parser = SafeConfigParser()
parser.optionxform=str
parser.read(config_file)
plist = biplist.readPlist(find('Info.plist', tmpdir))
for section_name in parser.sections():
    print '~~ Section:', section_name
    certificate = parser.get(section_name, 'certificate')
    plist_overwrite = parser.getboolean(section_name, 'info_plist_overwrite')
    entitlement_overwrite = parser.getboolean(section_name, 'entitlement_overwrite')
    generate_pkg = parser.getboolean(section_name, 'generate_macappstore_pkg')

    if not certificate:
        print ('Error: No certificate')
        exit(1)

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
        mobile_provisioning_profile= parser.get(section_name, 'ios_embedded.mobileprovision')
        if mobile_provisioning_profile:
            os.remove(find('embedded.mobileprovision', tmpdir))
            shutil.copyfile(mobile_provisioning_profile, application_path+'/embedded.mobileprovision')
        else:
            print("Error: need ios_embedded.mobileprovision profile")
            exit(1)
        cmd = ["codesign", "--sign", certificate, "--force", '--verbose']
        if entitlement_overwrite:
            cmd = cmd + ["--entitlements="+find("entitlement.plist", tmpdir)]
        cmd = cmd + [application_path]
        subprocess.call(cmd)
        zip('tmp', "./" + section_name, '.ipa')
    # platform MacOS
    if platform is "MacOS":
        cmd = ["codesign", "--deep", "--sign", certificate, "--force", '--verbose']
        if entitlement_overwrite:
            cmd = cmd + ["--entitlements="+find("entitlement.plist", tmpdir)]
        cmd = cmd + [application_path]
        subprocess.call(cmd)
        zip('tmp', "./" + section_name, '.zip')





#plistlib.writePlist(pl, "test.xml")
#pprint.pprint(plist)




