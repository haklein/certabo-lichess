# lichess.org board API client for CERTABO.com physical boards

This is a python3 based lichess board API client program for CERTABO physical boards. It's a proof of concept and probably still has some rough edges.

## Requirements

### Lichess API token

The API token can be created in the lichess preferences page ("API Access tokens"). Generate a personal access token and make sure to enable "Play games with the board API".

### python3 modules

- ndjson
- deprecated
- chess
- berserk lichess client (with board support, see https://github.com/rhgrant10/berserk/pull/10 )

simplejson must not be installed as it doesn't work with berserk
## Todo

* shake out bugs
* clean up logging (very chatty for now)

## License

This project is licensed under the GPL v3 license

