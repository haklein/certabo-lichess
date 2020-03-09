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

Calibration can be run with the optional "--calibrate" command line argument. Make sure to have the pieces on the correct places.

## Todo

* shake out bugs
* clean up logging (very chatty for now)

## License

This project is licensed under the GPL v3 license

