## Collection of scripts to upgrade FTOS
This is specific to our company build so it most likely will not work out of the box with your environment.  It was put together quickly and isn't meant to be pretty or user friendly

## Intallation
Its probably easiest to just install this in a virtual environment so as not to mess with the current modules
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
* add the path to the repository to your users path

## Distributing your binary files
* update `uploadbin.py` to accomodate your list of hostnames
  * currently this uses a mysql connection to pull this information but you should be able to pass any list of hostnames the `makeforks` function
* run `updatebin.py` to push your code version up

### notes
* assumes your binary files are in a directory called '/tftpboot/Dell/', you can change this in `peconnect.py`

## Running the upgrade script

### Prepare the switches for upgrade
* opengear connectivity will be validated and will be listed in the prepare output
* build directories to support pre,post and log files
* check that binfile exists on the remote devices and is valid (md5)
* add your binary to the 'alternate' slot A or B
  * alternate is determined by whichever boot slot is currently in use
* change the boot order in the config to load the alternate slot
* run pre upgrade commands (for diffs)
  * `show alarm |no-more`(fail if any exist)
  * `show vlt br |no-more` (fail if unexpected results)
  * `show int desc |no-more`
  * `show run |no-more`
  * `show logging |no-more`
  * `show hardware stack-unit 1 unit 0 execute-shell-cmd “ps” |no-more`
  * `show lldp nei |no-more`
* all command output will be copied to a file in the `~/ftosupgrade/<devicename>/<PRE>` directory
* all raw output will sent to `<devicename>/raw.log`
* a JSON file `<devicename>/devinfo.json` will be created to track history of the upgrade used for any necessary stateful information

### Upgrade process
* login to switch via opengear connection
* run the `reload` command and wait for prompt
* login to switch again via ssh
* run post checks (see pre-check commands)
* run diffs between pre and post checks
* look for any errors/anomolies (this needs to be defined)
* esclate if any issues

## Backout /  Downgrade
* TBD
