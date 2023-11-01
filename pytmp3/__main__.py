from concurrent.futures import ThreadPoolExecutor
from youtubesearchpython import PlaylistsSearch, VideosSearch, Playlist
from pytube import YouTube, Stream
from alive_progress import alive_bar
from typing import Any, Optional, Callable
from dataclasses import dataclass
from functools import partial
from contextlib import suppress
from mutagen.id3 import ID3, APIC, TIT2, TALB, TPE1, TLE
import subprocess
import argparse
import requests
import os
import re

MAX_WORKERS = 30
VIDEO_REGEX = r"^(?:https?:)?(?:\/\/)?(?:youtu\.be\/|(?:www\.|m\.)?youtube\.com\/(?:watch|v|embed)(?:\.php)?(?:\?.*v=|\/))([a-zA-Z0-9\_-]{7,15})(?:[\?&][a-zA-Z0-9\_-]+=[a-zA-Z0-9\_-]+)*(?:[&\/\#].*)?$"
PLAYLIST_REGEX = r"^(?!.*\?.*\bv=)https:\/\/www\.youtube\.com\/.*\?.*\blist=.*$"

@dataclass
class PlaylistInfo:
    url: str
    video_urls: list[str]
    title: str

def get_playlist_info_from_url(url:str) -> PlaylistInfo:
    playlist = Playlist.get(url)
    return PlaylistInfo(
        url,
        [video["link"] for video in playlist["videos"]],
        playlist["info"]["title"]
    )

def get_playlist_info_from_search_query(query:str) -> PlaylistInfo:
    result = PlaylistsSearch(query).result()
    first_result = result["result"][0]
    playlist_url = first_result["link"]
    return get_playlist_info_from_url(playlist_url)

def download_audio_from_url(output_path:str, url:str, playlist_name:str = None, on_progress: Optional[Callable[[Any, bytes, int], None]]=None, bar=None): 
    if bar != None:
        bar.text(f"Preparing download...")  

    # Get video data from youtube, select highest quality stream
    yt = YouTube(url, on_progress_callback=on_progress)
    audios = yt.streams.filter(only_audio=True)
    selected_audio: Stream = max(audios, key=lambda audio : audio.bitrate)
    if bar != None:
        bar.text(f"Downloading {selected_audio.title}...")

    # Download raw audio and determine filepath for new an mp3 file to replace it
    out_file = selected_audio.download(output_path)
    base, _ = os.path.splitext(out_file) 
    new_file = base + '.mp3'

    # Using FFMPEG convert to an MP3
    subprocess.call(f"ffmpeg -hide_banner -loglevel error -i \"{out_file}\" -ab 160k -ac 2 -ar 44100 -vn \"{new_file}\"", shell=True)
    
    # Add Metadata to file and save it
    audio = ID3(new_file)
    audio['APIC'] = APIC(
        encoding=3,
        mime='image/jpeg',
        type=3, desc='Cover',
        data=requests.get(yt.thumbnail_url).content
    )
    if playlist_name is not None:
        audio["TALB"] = TALB(encoding=3,text=playlist_name)
    audio["TIT2"] = TIT2(encoding=3, text=yt.title)
    audio["TPE1"] = TPE1(encoding=3,text=yt.author)
    audio["TLE"] = TLE(encoding=3,text=str(yt.length * 1000))
    audio.save()

    # Remove the old audio file
    with suppress(OSError):
        os.remove(out_file)

def download_audio_from_url_progress_bar(output_path:str, url:str):
    with alive_bar(manual=True, stats=False) as bar:
        def on_progress(stream: Stream, chunk: bytes, bytes_remaining: int):
            total_size = stream.filesize
            bytes_downloaded = total_size - bytes_remaining
            pct_completed = bytes_downloaded / total_size
            bar(pct_completed)
        
        download_audio_from_url(output_path, url, None, on_progress, bar)

def multithread_bulk_download_audio_urls(output_path:str, urls:str, playlist_title:str):
    with alive_bar(manual=True, stats=False) as bar:
        bar.text(f"Downloading {os.path.basename(output_path)}...")
        progress_dict = {}
        def on_progress(stream: Stream, chunk: bytes, bytes_remaining: int):
            total_size = stream.filesize
            bytes_downloaded = total_size - bytes_remaining
            file_pct_completed = bytes_downloaded / total_size
            progress_dict[stream.title] = file_pct_completed
            total_pct_completed = sum(progress_dict.values()) / len(urls)
            bar(total_pct_completed)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(partial(download_audio_from_url, output_path, playlist_name=playlist_title, on_progress=on_progress), urls)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="pytmp3",
        description="Easily download albums, playlists and songs off YouTube to MP3 format",
        epilog="⭐ Please star on GitHub! (https://github.com/Spacerulerwill/pytmp3) ⭐"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-p", "--playlist", help="Playlist or album search query or url", nargs="+")
    group.add_argument("-v", "--video", help="Song search query or url", nargs="+")
    parser.add_argument('-o', "--output", help="Output location for playlist, album or song. Defaults to downloads folder.", default=os.path.expanduser('~/Downloads'))
    args = parser.parse_args()

    playlist_input:list[str] = args.playlist
    video_input:list[str] = args.video
    output_path:str = args.output

    if playlist_input is not None:
        playlist_query = "".join(playlist_input)

        if bool(re.match(PLAYLIST_REGEX, playlist_query)):
            playlist_info = get_playlist_info_from_url(playlist_query)
        else:
            playlist_info = get_playlist_info_from_search_query(playlist_query)

        output_folder = os.path.join(output_path, playlist_info.title)

        with suppress(FileExistsError):
            os.mkdir(output_folder)

        multithread_bulk_download_audio_urls(output_folder, playlist_info.video_urls, playlist_info.title)

    elif video_input is not None:
        video_query = "".join(video_input)

        if bool(re.match(VIDEO_REGEX, video_query)):
            download_audio_from_url_progress_bar(output_path, video_query)
        else:
            search_result = VideosSearch(video_query).result()
            download_audio_from_url_progress_bar(output_path, search_result["result"][0]["link"])
            