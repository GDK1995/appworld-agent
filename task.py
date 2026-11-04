# STAGE 1.3
#python task.py
from appworld import AppWorld, load_task_ids

task_ids = load_task_ids("train")
task_id = task_ids[40] # Remove all songs from my Spotify song library and playlists that were released after 2021 year.
print(task_id)

with AppWorld(task_id=task_id, experiment_name="manual") as world:
    print("task:", world.task.instruction)
    world.execute("email = apis.supervisor.show_profile()['email']")
    world.execute("passwords = apis.supervisor.show_account_passwords()")
    world.execute("password = [p['password'] for p in passwords if p['account_name'] == 'spotify'][0]")
    world.execute("token = apis.spotify.login(username=email, password=password)['access_token']")

    world.execute("full_lib = []")
    world.execute("""
    for page in range(20):
        library = apis.spotify.show_song_library(access_token=token, page_index=page)
        if not library:
            break
        full_lib.extend(playlist)
    """)
    world.execute("all_songs = []")
    world.execute("""
    for lib in library:
        all_songs.append(lib['song_id'])
    """)
    print(world.execute("print(len(all_songs))"))

    world.execute("songs_obj = []")
    world.execute("""
    for song in all_songs:
        obj = apis.spotify.show_song(song_id=song)
        if int(obj['release_date'][:4]) > 2021:
            songs_obj.append(obj)
    """)
    print(world.execute("print(len(songs_obj))"))

    world.execute("""
    for rm_song in songs_obj:
        print(rm_song['song_id'])
        apis.spotify.remove_song_from_library(song_id=rm_song['song_id'], access_token=token)
    """)
    world.execute("library_after = apis.spotify.show_song_library(access_token=token, page_index=0, page_limit=20)")
    print(world.execute("print(len(library_after))"))
    print(world.evaluate())