# Parameter-grabber
Made and used this script while studying XSS attack surface.
<br>
This script is one part of multiple script I made to test for XSS for Open Bug Bounties.
<br>
You can use BurpSuite or other github tools for XSS testing. I wrote this to get a better grasp of what an XSS tool actually does (or should do).

## What do you use this for?
This script will intake a txt file composed of a URLs list to then export a list of the same URLs with the parameters found. For example if you have a file "URL.txt" with the website example.com and the script found parameters "input" and "search", then the output txt file will contain:
<br>
https://example.com?input=
<br>
https://example.com?search=
<br>
<br>
So now we have a list of URLs with each parameter separated and ready to be tested.
<br>
## Requirements
This script uses requests python library.
```
pip install requests
```
## Usage

```
python FindParameters.py <Directory_of_input_txt_file_of_URLs> <Directory_of_output_txt_file>
```
