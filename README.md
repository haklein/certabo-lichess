# lichess.org board API client for CERTABO.com physical boards

This is a python3 based lichess board API client program for CERTABO physical boards. It's a proof of concept and probably still has some rough edges.

## Requirements

### Lichess API token

The API token can be created in the [lichess preferences page ("API Access tokens")](http://lichess.org/account/oauth/token/create?description=Certabo&scopes[]=board:play). Generate a personal access token and make sure to enable "Play games with the board API". Store the token in a file named 'lichess.token' in the same directory.

### python3 modules

see `requirements.txt`. You can install the modules via `pip3 install --user -r requirements.txt`

simplejson must not be installed as it doesn't work with berserk

### virtual com port driver

On the mac you need to install the Silabs virtual com port driver. It can be downloaded from the CERTABO website: https://www.certabo.com/download/

### calibration

Calibration (mapping the chip IDs to pieces) can be run with the optional `--calibrate` command line argument. Make sure to have the pieces on the correct places before. If you want to add further pieces to the calibration, use the `--addpiece` argument (e.g. for adding a 2nd pair of queens, or adding multiple sets in different styles).

## Usage

### General
Run the python script, and start a game on Lichess that is compatible with the board API (not all speeds are supported, also depending if it is a rated game or not). Correspondence games are skipped by default, if you want to play them, use the `--correspondence` argument. The current games are ordered by lichess by importance. This script picks the first item (hence the game with the highest priority) from from that list. If there is no current game, it waits until a new game is created on lichess.

### Command line arguments

- `--calibrate` - This triggers a fresh calibration, maps the chip IDs to the pieces, ensure to have the starting position on the board
- `--addpiece` - This adds further pieces to the current calibration, e.g. for a second pair of queens or a different set with another theme
- `--correspondence` - Don't ignore correspondence games (ignoring them is the default behaviour)
- `--tokenfile` - Use a specific token file as lichess API token (defaults to `lichess.token` in the same directory)
- `--port` - Don't use USB serial port auto detection, but enforce a specific device file (might be helpful if you do have other devices that also use the SiLabs USB serial bridge chips, as they might falsely be detected as CERTABO board)
- `--devmode` - Connect to the http://lichess.dev sandbox instead of the real lichess servers
- `--quiet` - Don't print console output, just write the log file
- `--debug` - Be even more chatty in terms of console/log output

## Todo

* shake out bugs
* clean up logging (very chatty for now)

## License

This project is licensed under the GPL v3 license

