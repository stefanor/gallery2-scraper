from pathlib import Path
from unittest import TestCase

from bs4 import BeautifulSoup

from scrape import extract_albums, extract_images


class ScraperTests(TestCase):
    def test_image1(self):
        self.assertFindsImage('image1.html', {
            'description': 'hot ProcInfo Gain=45,N_M=2,OBC=5,Y=1,C=2,Sharp=400'
                           ',LuxMode=4,FaceNum=0    FocusArea=000011000',
            'title': 'Keeping warm by the fire. Evening before debcamp.',
            'url': 'http://example.net/main.php?g2_itemId=63006',
        })

    def test_album_no_image(self):
        self.assertFindsAlbum('album-no-image.html', {
            'owner': 'Joerg Jaspert',
            'title': 'DebConf17, Montreal, Canada',
            'url': 'http://example.net/main.php?g2_itemId=63538',
        })

    def assertFindsImage(self, filename, meta):
        p = Path(__file__).parent / 'data' / filename
        with p.open() as f:
            soup = BeautifulSoup(f, 'html5lib')
        try:
            image = next(extract_images('http://example.net/', soup))
        except StopIteration:
            raise AssertionError('Expected to find an image')
        self.assertEqual(image, meta)

    def assertFindsAlbum(self, filename, meta):
        p = Path(__file__).parent / 'data' / filename
        with p.open() as f:
            soup = BeautifulSoup(f, 'html5lib')
        try:
            album = next(extract_albums('http://example.net/', soup))
        except StopIteration:
            raise AssertionError('Expected to find an album')
        self.assertEqual(album, meta)
