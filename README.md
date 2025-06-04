This tool is intended for mass downloading mp3s from YouTube, adding tags to them, then structuring them nicely.

## What it does
0. Wipes the temp folder
1. Reads the songs from songs.csv
    - They must have the link, should at least have the song/album title and the artist name
2. Downloads the MP3s and thumbnails from YouTube using **yt-dlp** cli
3. Adds the thumbnails and song information to the mp3 tags
    - Thumbnails are always cut to 720x720
4. Structures the files like this
    ```
    MainFolder
    │   .gitignore
    │   EVERY FILE IN THIS FOLDER GETS DELETED
    │   main.py
    │   README.md
    │   songs.csv
    ├───All_MP3s
    │       song1.mp3
    │       song2.mp3 
    │       ...
    │
    └───Artists
        ├───Artist1
        │   ├───Album1
        │   │       song1cover.jpg
        │   │       Symlink -> song1.mp3
        │   │       song2cover.jpg
        │   │       Symlink -> song2.mp3
        │   ├───...
        │   ...
        │
        └───Artist2
            ├───...
            ...        
    ```

## Requirements
- yt-dlp.exe in PATH or in the same folder
- probably some python packages, idk


### Note
> This tool was originally intended for easy import into the Deezer streaming service. That's where the cover size limitation comes from.