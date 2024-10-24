# Parameter-grabber
This script was developed while studying the XSS attack surface and is part of a suite of tools created for testing XSS vulnerabilities on Open Bug Bounties.

## What does this script do?
The `Parameter-grabber` script processes a text file containing a list of URLs and outputs a new file with those URLs expanded to include any parameters found. For example, if you start with a file named `URL.txt` containing `https://example.com`, and the script detects parameters like `input` and `search`, the output file will contain:
<br>
https://example.com?input=
<br>
https://example.com?search=
<br>
<br>
With this list of URLs and their respective parameters, you'll have a ready-to-use dataset testing.
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
