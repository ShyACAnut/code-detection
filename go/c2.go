	return 0, 0, err
				}

				negativeIndex = 0
			case 'b':
				if helper.numberFormat == hex {
					break
				}
				fallthrough
			case 'o', 'x':
				if i == 0 && b[i] != '0' {
					return 0, 0, NewParseError("incorrect base format, expected leading '0'")
				}

				if i != 1 {
					return 0, 0, NewParseError(fmt.Sprintf("incorrect base format found %s at %d index", string(b[i]), i))
				}

				if err := helper.Determine(b[i]); err != nil {
					return 0, 0, err
				}
			default:
				if isWhitespace(b[i]) {
					break loop
				}

				if isNewline(b[i:]) {
					break loop
				}

				if !(helper.numberFormat == hex && isHexByte(b[i])) {
					if i+2 < len(b) && !isNewline(b[i:i+2]) {
						return 0, 0, NewParseError("invalid numerical character")
					} else if !isNewline([]rune{b[i]}) {
						return 0, 0, NewParseError("invalid numerical character")
					}

					break loop
				}
			}
		}
	}

	return helper.Base(), i, nil
}