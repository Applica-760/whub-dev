package main

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/Applica-760/whub/backend/internal/manifest"
)

func main() {
	if len(os.Args) != 3 || os.Args[1] != "projects" || os.Args[2] != "--json" {
		fmt.Fprintln(os.Stderr, "usage: whub projects --json")
		os.Exit(2)
	}

	document, err := manifest.LoadDefault()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if err := json.NewEncoder(os.Stdout).Encode(document.Projects); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
