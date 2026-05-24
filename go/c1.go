

		if isLitValue(lv, b) {
			n = len(lv)
		}
	}

	if n == 0 {
		return 0, NewParseError("invalid boolean value")
	}

	return n, nil
}