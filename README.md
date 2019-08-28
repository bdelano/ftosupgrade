##collection of scripts to upgrade FTOS
This is specific to our company build so it most likely will not work out of the box with your environment.  It was put together quickly and isn't meant to be pretty or user friendly
## Distributing your binary files
Its probably easiest to just install this in a virtual environment so as not to mess with the current modules
* create environment `virtualenv ftosupgrade`
* update uploadbin.py to accomodate your list of hostnames
* run `updatebin.py` to push your code version up
### notes
* assumes your binary files are in '/tftpboot/Dell/', you can change this in `peconnect.py`
* we use trigger for remote connecting devices so our username and passwords are pulled from that framework
