# Parameter-grabber
Made and used this script while studying XSS attacking surface

## What do you use this for?
This script will intake a txt file composed of a URLs list to then export a list of the same URLs with the parameters found. For example if you tried grabbing parameters from example.com and the script found parameters "input" and "search", then the output txt file will contain:
<br>
https://example.com?input=
<br>
https://example.com?search=
<br>

## Requirements
This script works with requests python library
```
pip install requests
```
## Usage
This script works with requests python library
```
python FindParameters.py <Directory of input txt file of URLs> <Directory of output txt file>
```
