 Sections{}, awserr.New(ErrCodeUnableToReadFile, "unable to open file", err)
	}
	defer f.Close()

	return Parse(f)
}