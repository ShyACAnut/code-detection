	case '\\': // backslash
	default:
		return false
	}

	return value[len(value)-1] == '\\'
}