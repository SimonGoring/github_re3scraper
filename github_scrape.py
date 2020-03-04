#!/usr/bin/env python3
''' GitHub Python scraper

Linking to github repositories to find all repositories that contain code
related to the Re3Data databases.

This code hits the abuse detection mechanism, even with the pausing.
'''

from github import Github
from py2neo import Graph
from py2neo.data import Node, Relationship
import json
import random
import urllib
import requests
import re
import time
import csv
import sys

with open('connect_remote.json') as f:
    data = json.load(f)

print("Connecting to the remote graph. . .")
graph = Graph(**data)

tx = graph.begin()

# The use of the >>>!!!<<< is used to show deprecation apparently.
# This returns 2255 research databases from re3data.

cypher = """MATCH (:TYPE {type:"schema:CodeRepository"})-[:isType]-(cr:OBJECT)-[:Target]-(:ANNOTATION)-[tar:Target]-(ot:OBJECT)-[:isType]-(:TYPE {type:"schema:DataCatalog"})
    WITH COLLECT(DISTINCT ot.name) AS goodies
    MATCH (ob:OBJECT)-[:isType]-(:TYPE {type:"schema:DataCatalog"})
    WHERE (NOT ob.name IN goodies)
    RETURN DISTINCT ob"""

print("Matching existing repositories")
dbs = graph.run(cypher).data()

with open('gh.token') as f:
    token = json.load(f)

g = Github(token['token'])

gitadd = open('cql/github_linker.cql', mode="r")
git_cql = gitadd.read()

random.shuffle(dbs)

for db in dbs:
    print("Running graphs for", db['ob']['name'])
    url = re.sub("http*://", '', db['ob']['url'])
    repositories = []

    if len('"' + db['ob']['name'] + '" "' + url + '" in:file') > 127:
        searchString = '"' + db['ob']['name'] + '" in:file'
    else:
        searchString = '"' + db['ob']['name'] + '" "' + url + '" in:file'

    rate_limit = g.get_rate_limit()
    print("   There are " + str(rate_limit.search.remaining) + " calls to GitHub remaining.")

    if rate_limit.search.remaining < 2:
        print("   Rate limit reached, pausing for 10 seconds.")
        time.sleep(10)

    hitexcept = True
    pausetime = 30
    while hitexcept:
        try:
            content_files = g.search_code(query=searchString)
            hitRepos = content_files.totalCount
            print("   Returning " + str(content_files.totalCount) + " results.")
            hitexcept = False
        except Exception as ex:
            f = open('data/skipped_re3.txt', 'a')
            f.write("'" + searchString + "'" + " " + str(ex) + "\n")
            f.close()

            print("Sleeping for " + str(pausetime) + " seconds")
            time.sleep(pausetime)
            pausetime = pausetime + 30

    if hitRepos == 1000:
        print("   **** There are more than 1000 results returned. ***")
        f = open('data/skipped_re3.txt', 'a')
        f.write(searchString + " over 1k results\r\n")
        f.close()

    if hitRepos == 0:
        next

    print('Pulling content')

    for content in content_files:
        time.sleep(1)
        hitexcept = True
        pausetime = 30

        while hitexcept:
            try:
                repo = content.repository
                hitexcept = False
            except Exception as ex:
                time.sleep(pausetime)
                pausetime = pausetime + 30
                f = open('data/skipped_re3.txt', 'a')
                f.write(searchString + " " + str(ex) + "\n")
                f.close()

        repElem = { 'ghid': repo.id,
                    'ghurl': repo.html_url,
                    'ghdescription': repo.description,
                    'ghname': repo.full_name ,
                    'otid':db['ob']['id'] }
        repositories.append(repElem)

        print(repElem)

    repositories = list({v['ghid']:v for v in repositories}.values())
    if len(repositories) == 0:
        continue
    print("   Pushing information for " + str(len(repositories)) + " public repositories.")
    for rep in repositories:
        if rep['ghdescription'] is None:
            rep['ghdescription'] = ''
        connect = """MATCH (oba:OBJECT)
                 WHERE oba.id = {ghid}
                 MATCH (obb:OBJECT)
                 WHERE obb.id = {otid}
                 WITH oba, obb
                 MATCH (oba)<-[:Target]-(a:ANNOTATION)-[:Target]->(obb)
                 RETURN a
                 """
        test = graph.run(connect, rep)
        if len(test.data()) == 0:
            print("    * Adding repository to the graph.")
            graph.run(git_cql, rep)
