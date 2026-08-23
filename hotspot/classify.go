package hotspot

import (
	"bytes"
	"path/filepath"
	"strings"
)

type classification struct {
	language             Language
	text                 bool
	excludeExtensionless bool
}

var extensionLanguages = map[string]Language{
	".go": LanguageGo, ".md": LanguageMarkdown, ".markdown": LanguageMarkdown,
	".mdx": LanguageMDX, ".astro": LanguageAstro, ".py": LanguagePython, ".pyi": LanguagePython,
	".java": LanguageJava, ".kt": LanguageKotlin, ".kts": LanguageKotlin,
	".js": LanguageJavaScript, ".mjs": LanguageJavaScript, ".cjs": LanguageJavaScript,
	".ts": LanguageTypeScript, ".mts": LanguageTypeScript, ".cts": LanguageTypeScript,
	".jsx": LanguageJSX, ".tsx": LanguageTSX, ".html": LanguageHTML, ".htm": LanguageHTML,
	".css": LanguageCSS, ".xml": LanguageXML, ".xsd": LanguageXML, ".svg": LanguageXML,
	".xslt": LanguageXML, ".xsl": LanguageXML, ".plist": LanguageXMLPlist,
	".json": LanguageJSON, ".jsonc": LanguageJSONFamily, ".json5": LanguageJSONFamily,
	".yaml": LanguageYAML, ".yml": LanguageYAML, ".toml": LanguageTOML,
	".tf": LanguageTerraform, ".tfvars": LanguageTerraform, ".gradle": LanguageGradle,
	".sql": LanguageSQL, ".bash": LanguageBash, ".zsh": LanguageZsh, ".sh": LanguagePOSIXShell,
	".dockerfile": LanguageDockerfile,
}

func classify(relative string, content []byte) classification {
	name := filepath.Base(relative)
	lowerName := strings.ToLower(name)
	if strings.HasSuffix(lowerName, ".plist") && bytes.HasPrefix(content, []byte("bplist00")) {
		return classification{LanguageBinaryPlist, false, false}
	}
	if looksBinary(content) {
		return classification{LanguageBinary, false, false}
	}
	if isDockerfileName(name) {
		return classification{LanguageDockerfile, true, false}
	}
	if name == "Vagrantfile" {
		return classification{LanguageVagrantfile, true, false}
	}
	if lowerName == "build.gradle" || lowerName == "settings.gradle" || lowerName == "build.gradle.kts" || lowerName == "settings.gradle.kts" {
		return classification{LanguageGradle, true, false}
	}
	extension := strings.ToLower(filepath.Ext(name))
	if language, known := extensionLanguages[extension]; known {
		return classification{language, true, false}
	}
	if extension == "" {
		if language, ok := shebangLanguage(content); ok {
			return classification{language, true, false}
		}
		return classification{LanguageUnknown, true, true}
	}
	return classification{LanguageUnknown, true, false}
}

func isDockerfileName(name string) bool {
	lower := strings.ToLower(name)
	if lower == "dockerfile" || lower == "containerfile" {
		return true
	}
	if strings.HasPrefix(lower, "dockerfile.") || strings.HasPrefix(lower, "containerfile.") {
		suffix := strings.TrimPrefix(strings.TrimPrefix(lower, "dockerfile."), "containerfile.")
		if suffix == "" || len(suffix) > 64 {
			return false
		}
		for _, character := range suffix {
			if !(character >= 'a' && character <= 'z' || character >= '0' && character <= '9' || character == '_' || character == '-' || character == '.') {
				return false
			}
		}
		return true
	}
	return false
}

func shebangLanguage(content []byte) (Language, bool) {
	prefix := content
	if len(prefix) > 256 {
		prefix = prefix[:256]
	}
	if newline := bytes.IndexByte(prefix, '\n'); newline >= 0 {
		prefix = prefix[:newline]
	}
	line := strings.TrimSuffix(string(prefix), "\r")
	if !strings.HasPrefix(line, "#!") || strings.ContainsRune(line, '\x00') {
		return "", false
	}
	fields := strings.Fields(strings.TrimSpace(strings.TrimPrefix(line, "#!")))
	if len(fields) == 0 {
		return "", false
	}
	interpreter := filepath.Base(fields[0])
	if fields[0] == "/usr/bin/env" {
		if len(fields) != 2 || strings.HasPrefix(fields[1], "-") {
			return "", false
		}
		interpreter = fields[1]
	} else if len(fields) != 1 {
		return "", false
	}
	switch interpreter {
	case "bash":
		return LanguageBash, true
	case "zsh":
		return LanguageZsh, true
	case "sh", "dash", "ash":
		return LanguagePOSIXShell, true
	case "python", "python3":
		return LanguagePython, true
	case "node", "nodejs":
		return LanguageJavaScript, true
	default:
		return "", false
	}
}

func looksBinary(content []byte) bool {
	prefix := content
	if len(prefix) > 512 {
		prefix = prefix[:512]
	}
	for _, value := range prefix {
		if value == 0 {
			return true
		}
		if value < 0x20 && value != '\n' && value != '\r' && value != '\t' && value != '\f' {
			return true
		}
	}
	return false
}

func physicalLines(content []byte) int64 {
	if len(content) == 0 {
		return 0
	}
	lines := int64(bytes.Count(content, []byte{'\n'}))
	if content[len(content)-1] != '\n' {
		lines++
	}
	return lines
}
