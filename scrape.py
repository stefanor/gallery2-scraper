#!/usr/bin/env python3
# Copyright 2019 Stefano Rivera <stefano@rivera.za.net>
# Licensed under the ISC license.

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup, NavigableString
import requests
import yaml


def main():
    p = argparse.ArgumentParser()
    p.add_argument('url', help='Gallery2 base URL')
    p.add_argument('output', help='Destination directory')
    args = p.parse_args()

    scraper = Scraper(args.url)
    try:
        scraper.scrape(Path(args.output))
    except KeyboardInterrupt:
        sys.exit('Interrupted')


def extract_albums(album_url, soup):
    untitled_index = 0
    for album in soup.find_all('td', class_='giAlbumCell'):
        url = urljoin(album_url, album.a['href'])

        desc_block = album.next_sibling
        if isinstance(desc_block, NavigableString):
            desc_block = desc_block.next_sibling
        if desc_block is None:
            desc_block = album

        title = desc_block.find('p', class_='giTitle')
        if title:
            title = title.text.strip()
            title = re.sub(r'^Album: ', '', title)
        else:
            title = 'Untitled Album {}'.format(untitled_index)
            untitled_index += 1

        info_block = desc_block.find('div', class_='giInfo')
        owner = None
        if info_block:
            owner_block = info_block.find('div', class_='owner')
            if owner_block:
                owner = owner_block.text.strip()
                owner = re.sub(r'^Owner: ', '', owner)

        yield {
            'url': url,
            'title': title,
            'owner': owner,
        }


def extract_images(album_url, soup):
    for img in soup.find_all('td', class_='giItemCell'):
        url = urljoin(album_url, img.a['href'])

        desc_block = img.next_sibling
        if isinstance(desc_block, NavigableString):
            desc_block = desc_block.next_sibling
        if desc_block is None:
            desc_block = img  # WTF

        title = desc_block.find('p', class_='giTitle')
        if title:
            title = title.text.strip()

        description = desc_block.find('p', class_='giDescription')
        if description:
            description = description.text.strip()

        yield {
            'url': url,
            'title': title,
            'description': description,
        }


class Scraper:
    def __init__(self, url):
        self.base_url = url

    def scrape(self, output):
        self.scrape_main(output)

    def scrape_main(self, output):
        main_url = urljoin(self.base_url, 'main.php')
        if not output.exists():
            output.mkdir()
        self.scrape_album(output, {
            'title': '',
            'owner': 'DebConf',
            'url': main_url,
        })
        print()

    def slug(self, string):
        slug = re.sub(r'[^A-Za-z0-9 ]*', '', string)
        slug = re.sub(r'\s+', '-', slug)
        return slug[:100]

    def scrape_album(self, parent_path, album):
        slug = self.slug(album['title'])
        path = parent_path / slug
        if not path.exists():
            path.mkdir()

        meta_fn = path / 'gallery_meta.yml'
        if meta_fn.exists():
            return
        print('\nDownloading {} -> {}\n{}'.format(
                album['title'], path, album['url']))

        self.scrape_sub_albums(album['url'], path)
        for soup in self.paginated_soup(album['url']):
            for i, image in enumerate(extract_images(album['url'], soup)):
                self.scrape_image(i, image, path)

        with meta_fn.open('w') as f:
            yaml.safe_dump(album, f, default_flow_style=False)

    def scrape_image(self, index, image, path):
        m = re.match(r'.*[?&]g2_itemId=(\d+)(?:&.*|$)', image['url'])
        id_ = m.group(1)
        dl_url = urljoin(self.base_url, 'main.php?' + urlencode({
            'g2_view': 'core.DownloadItem',
            'g2_itemId': id_,
        }))

        basename = '{:03}'.format(index)
        if image['title']:
            basename += '-' + self.slug(image['title'])
        meta_fn = path / (basename + '.yml')

        if meta_fn.exists():
            return

        sys.stdout.write('.')
        sys.stdout.flush()

        r = requests.get(dl_url, stream=True)
        if r.status_code != 200:
            raise Exception(
                'Got HTTP {} from {}'.format(r.status_code, dl_url))
        content_type = r.headers['Content-Type']

        if content_type == 'gallery/linkitem':
            return

        extension = {
            'image/png': '.png',
            'image/jpeg': '.jpg',
            'video/quicktime': '.mov',
            'application/unknown': '',
        }[content_type]

        fn = path / (basename + extension)
        with fn.open('wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                f.write(chunk)

        with meta_fn.open('w') as f:
            yaml.safe_dump(image, f, default_flow_style=False)


    def scrape_sub_albums(self, url, path):
        for soup in self.paginated_soup(url):
            for album in extract_albums(url, soup):
                self.scrape_album(path, album)

    def paginated_soup(self, url):
        while True:
            r = requests.get(url)
            soup = BeautifulSoup(r.content, 'html5lib')
            yield soup

            paginator = soup.find('div', class_='gbNavigator')
            if not paginator:
                break
            next_ = paginator.find(class_='next')
            if not next_:
                break
            url = urljoin(url, next_['href'])


if __name__ == '__main__':
    main()
