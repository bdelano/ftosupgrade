# Collection of scripts to upgrade FTOS
This is specific to our company build so it most likely will not work out of the box with your environment!  
The code was put together quickly and isn't meant to be pretty or user friendly, but the working tool should be :)

<!-- MDTOC maxdepth:6 firsth1:2 numbering:0 flatten:0 bullets:1 updateOnSave:1 -->

- [Running the upgrade script](#running-the-upgrade-script)   
   - [Uploading binary files to multiple devices](#uploading-binary-files-to-multiple-devices)   
   - [Prepare the Switches for Upgrade](#prepare-the-switches-for-upgrade)   
   - [Upgrade the Switch](#upgrade-the-switch)   
   - [Backout /  Downgrade](#backout-downgrade)   
- [Tutorial](#tutorial)   
- [Intallation](#intallation)   
- [To Do](#to-do)   

<!-- /MDTOC -->

## Running the upgrade script
### Uploading binary files to multiple devices
* you can specify either a list of devices or a region
* script will run multiple scp sessions at once (default 20)
* assumes your binary files are in a directory called '/tftpboot/Dell/', you can change in `main.py`

### Prepare the Switches for Upgrade
* opengear connectivity will be validated and will be listed in the prepare output
* prompt will be compared between opengear and ssh to device
* build directories to support pre,post and log files
* check that binfile exists on the remote devices and is valid (md5)
  * if binfile does not exist on the device it will be uploaded and validated
  * this will only work if the appropriate bin file is in the `/tftpboot/Dell/` directory
* add your binary to the 'alternate' slot A or B
  * alternate is determined by whichever boot slot is currently in use
* change the boot order in the config to load the alternate slot
* run pre check commands (for diffs)
  * `show alarm |no-more`(fail if any exist)
  * `show vlt br |no-more` (fail if unexpected results)
  * `show hardware stack-unit 1 unit 0 execute-shell-cmd “ps” |no-more` (fail if status is blocking and port is up)
  * `show int desc |no-more`
  * `show run |no-more`
  * `show logging |no-more`
  * `show lldp nei |no-more`
* all command output will be copied to a file in the `~/ftosupgrade/<devicename>/pre` directory
* all raw output will sent to `<devicename>/raw.log`
* a JSON file `<devicename>/devinfo.json` will be created to track history of the upgrade used for any necessary stateful information

### Upgrade the Switch
* check if the switch is already upgraded
* login to switch via opengear connection
* run the `reload` command acknowledge and wait for prompt
* login to switch again via ssh
* run post checks (see pre-check commands)
* all command output will be copied to a file in the `~/ftosupgrade/<devicename>/post` directory
* run diffs between pre and post checks
* look for any errors/anomolies (this needs to be defined)
* esclate if any issues

### Backout /  Downgrade
* restore previous boot config
* TBD

## Tutorial
To use the script login to an appropriate noctool box and type the appropriate `ftosupgrade` command (see examples below).  The script will then create the necessary directories in `~/ftosupgrade` e.g. `/home/bdelano/ftosupgrade`. You can then change to this directory to see all the logs of your interactions with the switches.

* You will to run the `gong` command and login to at least 1 device as this uses your stored trigger credentials.

* Examples
  * `ftosupgrade --help` This will show a help menu with all the options
  * `ftosupgrade -d iad301-tor01-e02-stg,iad301-tor01-e02-stg -b FTOS-SK-9.14.1.0.bin -t upload` uploads binary to 2 switches
  * `ftosupgrade -r ap-southeast -b FTOS-SK-9.14.1.0.bin -t upload` uploads binary to all switches in ap-southeast
  * `ftosupgrade -d iad301-tor01-e02-stg -b FTOS-SK-9.14.1.0.bin -t prepare` This command will prepare this switch for upgrade
  * `ftosupgrade -d iad301-tor01-e02-stg,iad301-tor01-e02-stg -b FTOS-SK-9.14.1.0.bin -t prepare` prepares 2 switches  
  * `ftosupgrade -d iad301-tor01-e02-stg -b FTOS-SK-9.14.1.0.bin -t upgrade` Runs the prepare script and then runs the upgrade script which will reload the devices and do post checks
  * `ftosupgrade -d iad301-tor01-e02-stg -b FTOS-SK-9.14.1.0.bin -t backout` At the moment this just resets the boot order, you will need to reload manually as this assumes there was some issue

## Intallation
*CAUTION: only admins need to do this, it should already be installed!*

Its probably easiest to just install this in a virtual environment so as not to mess with the current modules
* use a *nix* box, tested on ubuntu 16.4
* create environment `virtualenv ftosupgrade`
* then run `source ftosupgrade/bin/activate`
* add the required python modules
  * MySQL-python (only if you are going to use a remote sql server)
  * paramiko
  * scp
  * pexpect
  * termcolor
  * terminaltables
* clone this repository
* add a `localauth.py` file with the necessary information (see example file)
* add the path to the repository to your users path or setup a link

## To Do
* need gracefully fail when opengear connect sometimes fails
* need to add longer pause before running post commands (trying 60 seconds for now)
