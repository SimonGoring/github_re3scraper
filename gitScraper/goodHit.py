from re import search
import json


def goodHit(query, text):
    """Check for expected query call in file content.

    Parameters
    ----------
    query : str
        The URL and database name.
    text : list
        The File contents, including highlighted fragments.

    Returns
    -------
    type
        Description of returned object.

    """

    match = False
    for i in query:
        test = r'.*' + i + r'.*'
        checklib = list(map(lambda x: search(test, x.get('fragment')), text))
        if not(all(matches is None for matches in checklib)):
            match = True
            break

    if match is not True:
        f = open("fail_log.txt", "a")
        textdump = {'query': query,
                    'text': list(map(lambda x: x.get('fragment'), text))}
        f.write(json.dumps(textdump) + "\n")
        f.close()
    else:
        f = open("pass_log.txt", "a")
        textdump = {'query': query,
                    'text': list(map(lambda x: x.get('fragment'), text))}
        f.write(json.dumps(textdump) + "\n")
        f.close()
    return match
