import os
import subprocess
from PIL import Image
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
import json
import shutil
import csv
import re

def sanitize_filename(name):
    return "".join(c for c in name if c not in '<>:"/\\|?*').strip()

def parse_time_range(range_str):
    if not range_str:
        return None
    s = range_str.strip()
    try:
        start_str, end_str = s.split('-', 1)
        # allow numeric input; drop fractional part if provided
        start_s = int(float(start_str))
        end_s = int(float(end_str))
    except Exception:
        raise ValueError(f"Invalid time range format: {s}. Expected seconds-seconds (integers)")

    if end_s <= start_s:
        raise ValueError(f"End time must be greater than start time: {s}")

    def sec_to_hms(sec):
        hh = sec // 3600
        mm = (sec % 3600) // 60
        ss = sec % 60
        return f"{hh:02}:{mm:02}:{ss:02}"

    return f"{sec_to_hms(start_s)}-{sec_to_hms(end_s)}"

def download_audio_and_thumbnail(url, output_dir, artist, album, song_title, time_range=None):
    command = [
        "yt-dlp",
        "-f", "bestaudio",
        "--write-thumbnail",
        "--write-info-json",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
    ]

    if time_range:
        norm = parse_time_range(time_range)
        print(f"Downloading only section: {norm}")
        command += ["--download-sections", f"*{norm}"]

    command += [
        "-o", os.path.join(output_dir, "downloaded.%(ext)s"),
        url
    ]
    subprocess.run(command, check=True)

    full_title = f"{artist} - {album} - {song_title}"
    sanitized_title = sanitize_filename(full_title)
    base = os.path.join(output_dir, sanitized_title)
    
    downloaded_mp3 = os.path.join(output_dir, "downloaded.mp3")
    mp3_path = base + ".mp3"
    if os.path.exists(downloaded_mp3):
        os.rename(downloaded_mp3, mp3_path)
    
    thumb_path = None
    for ext in ['jpg', 'webp', 'png']:
        downloaded_thumb = os.path.join(output_dir, f"downloaded.{ext}")
        if os.path.exists(downloaded_thumb):
            thumb_path = base + f'.{ext}'
            os.rename(downloaded_thumb, thumb_path)
            break

    if not os.path.exists(mp3_path):
        raise FileNotFoundError(f"Missing MP3 file: {mp3_path}")
    if not thumb_path:
        raise FileNotFoundError("Missing thumbnail file.")

    return mp3_path, thumb_path

def crop_thumbnail(thumbnail_path):
    img = Image.open(thumbnail_path)
    width, height = img.size
    min_side = min(width, height)
    left = (width - min_side) // 2
    top = (height - min_side) // 2
    right = left + min_side
    bottom = top + min_side
    img_cropped = img.crop((left, top, right, bottom)).resize((720, 720))
    square_path = thumbnail_path.rsplit('.', 1)[0] + '.jpg'
    img_cropped.save(square_path, format='JPEG')
    return square_path

def add_tags(mp3_path, cover_path, artist, title, album):
    audio = EasyID3(mp3_path)
    audio['artist'] = artist
    audio['title'] = title
    audio['album'] = album
    audio.save()

    audio = ID3(mp3_path)
    with open(cover_path, 'rb') as img:
        audio['APIC'] = APIC(
            encoding=3,
            mime='image/jpeg',
            type=3,
            desc='Cover',
            data=img.read()
        )
    audio.save()

def clear_temp_folder(temp_dir):
    if os.path.exists(temp_dir):
        for f in os.listdir(temp_dir):
            try:
                os.remove(os.path.join(temp_dir, f))
            except Exception:
                pass
    else:
        os.makedirs(temp_dir)

def organize_files(song_title, artist_name, mp3_path, cover_path, all_mp3_dir, output_dir):
    os.makedirs(all_mp3_dir, exist_ok=True)
    mp3_filename = os.path.basename(mp3_path)
    unified_mp3_path = os.path.join(all_mp3_dir, mp3_filename)
    shutil.move(mp3_path, unified_mp3_path)

    base_dir = os.path.dirname(__file__)
    artist_folder = os.path.join(base_dir, "Artists", artist_name)
    song_folder = os.path.join(artist_folder, song_title)
    os.makedirs(song_folder, exist_ok=True)

    cover_dest = os.path.join(song_folder, os.path.basename(cover_path))
    shutil.move(cover_path, cover_dest)

    symlink_path = os.path.join(song_folder, mp3_filename)
    if not os.path.exists(symlink_path):
        os.symlink(os.path.relpath(unified_mp3_path, song_folder), symlink_path)

    return unified_mp3_path, cover_dest

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "temp")
    all_mp3_dir = os.path.join(base_dir, "All_MP3s")
    csv_file_path = os.path.join(base_dir, "songs.csv")

    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        reader = list(csv.DictReader(csvfile, delimiter=',', quotechar='"'))
    
    for row in reader:
        clear_temp_folder(output_dir)
        url = row['link'].strip()
        album = row['album_title'].strip()
        song_title = row['song_title'].strip()
        
        artist = row['artist_name'].strip()
        if not artist:
            artist = "Unknown"
        if not album and not song_title:
            album = "Unknown"
            song_title = "Unknown"
        elif not album:
            album = song_title
        elif not song_title:
            song_title = album

        # read optional time range from CSV: try 'time_range' first, then 'time'
        time_range = ''
        if 'time_range' in row:
            time_range = row['time_range'].strip()
        elif 'time' in row:
            time_range = row['time'].strip()

        print(f"Processing: {url}")
        mp3_path, thumbnail_path = download_audio_and_thumbnail(url, output_dir, artist, album, song_title, time_range if time_range else None)
        square_thumb = crop_thumbnail(thumbnail_path)

        add_tags(mp3_path, square_thumb, artist, song_title, album)

        final_mp3, final_thumb = organize_files(album, artist, mp3_path, square_thumb, all_mp3_dir, output_dir)
        print(f"Stored in folder: {os.path.dirname(final_thumb)}\n")

if __name__ == '__main__':
    main()
