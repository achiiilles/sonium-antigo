        // The lead shelf is listening history, so opening Home after playing
        // something is exactly when it needs re-fetching.
        LaunchedEffect(currentFeed) {
            // Recarga automática desativada para manter navegação estável sem sobrescrever a Home
            // if (currentFeed == MainViewModel.Feed.HOME) viewModel.onHomeShown()
            // Likewise for Library: a playlist created or a song liked since it
            // was last fetched is a change to exactly this page.
            if (currentFeed == MainViewModel.Feed.LIBRARY) viewModel.onLibraryShown()
        }