import os

path = "app/src/main/java/com/music/bitchord/MainActivity.kt"
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    target = """    LaunchedEffect(currentFeed) {
        if (currentFeed == MainViewModel.Feed.HOME) viewModel.onHomeShown()
        // Likewise for Library: a playlist created or a song liked since it
        // was last fetched is a change to exactly this page.
        if (currentFeed == MainViewModel.Feed.LIBRARY) viewModel.onLibraryShown()
    }"""
    
    replacement = """    LaunchedEffect(currentFeed) {
        // Desativada recarga automatica silenciosa que sobrescreve a Home ao voltar da reproducao
        // if (currentFeed == MainViewModel.Feed.HOME) viewModel.onHomeShown()
        // Likewise for Library: a playlist created or a song liked since it
        // was last fetched is a change to exactly this page.
        if (currentFeed == MainViewModel.Feed.LIBRARY) viewModel.onLibraryShown()
    }"""
    
    if target in content:
        content = content.replace(target, replacement)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("MainActivity.kt patched: disabled automatic silent home reload")
    else:
        print("Target block in MainActivity.kt not found or already patched")
