# vsresign
Visionaire Studio Codesign python Tool


## Install
* Use setuptools: `easy_install biplist`

## Usage
edit your config.ini file

show certificates:
`vsresign.py --list`

resign iOS application:
`vsresign.py -c config.ini -i visplayer.ipa`
resign MacOS application:
`vsresign.py -c yourconfig.ini visplayer.zip`