# STAGE 1.3
#python task_2.py
from appworld import AppWorld, load_task_ids

task_id = "b7a9ee9_3" # Follow all artists of all indie-genre songs in any of my playlists on Spotify.

with AppWorld(task_id=task_id, experiment_name="manual") as world:
    world.execute("email = apis.supervisor.show_profile()['email']")
    world.execute("passwords = apis.supervisor.show_account_passwords()")
    world.execute("password = [p['password'] for p in passwords if p['account_name'] == 'spotify'][0]")
    world.execute("token = apis.spotify.login(username=email, password=password)['access_token']")

    world.execute("all_playlists = []")
    world.execute("""
    for page in range(20):
        playlist = apis.spotify.show_playlist_library(access_token=token, page_index=page, page_limit=20)
        if not playlist:
            break
        all_playlists.extend(playlist)
    """)

    world.execute("all_songs_of_playlist = set()")
    world.execute("""
    for playlist in all_playlists:
        all_songs_of_playlist.update(playlist['song_ids'])
    """)

    world.execute("indie_song = []")
    world.execute("""
    for song in all_songs_of_playlist:
        song = apis.spotify.show_song(song_id=song)
        if song['genre'] == 'indie':
            indie_song.append(song)
    """)

    world.execute("artists = set()")
    world.execute("""
    for song in indie_song:
        for atrist in song['artists']:
            artists.add(atrist['id'])
    """)

    world.execute("to_follow = set()")
    world.execute("""
    for artist in artists:
        isFollowing = apis.spotify.show_artist_following(artist_id=artist, access_token=token)
        if not isFollowing['following']:
            to_follow.add(artist)
    """)

    world.execute("messages = []")
    world.execute("""
    for artist in to_follow:
        messages.append(apis.spotify.follow_artist(artist_id=artist, access_token=token))
    """)

    world.execute("after_indie_song = []")
    world.execute("""
    for song in all_songs_of_playlist:
        song = apis.spotify.show_song(song_id=song)
        if song['genre'] == 'indie':
            after_indie_song.append(song)
    """)
    print(world.execute("print(indie_song)"))
    print(world.execute("print(after_indie_song)"))

    world.execute("apis.supervisor.complete_task()")
    print(world.evaluate())