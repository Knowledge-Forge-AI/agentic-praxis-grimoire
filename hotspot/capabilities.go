package hotspot

func capability(surface string, languages []Language, lines, statements, symbols, cyclomatic, nesting, procedural, structural Availability, confidence Confidence) SurfaceCapability {
	return SurfaceCapability{
		Surface: surface, Languages: languages, Classification: AvailabilityExact,
		Lines: lines, Statements: statements, Symbols: symbols, Cyclomatic: cyclomatic,
		Nesting: nesting, ProceduralRegions: procedural, StructuralMetrics: structural,
		Confidence: confidence,
	}
}

func frozenCapabilities() []SurfaceCapability {
	E, S, U, N := AvailabilityExact, AvailabilityStructural, AvailabilityUnavailable, AvailabilityNotApplicable
	return []SurfaceCapability{
		capability("Go", []Language{LanguageGo}, E, E, E, E, E, E, E, ConfidenceHigh),
		capability("Markdown", []Language{LanguageMarkdown}, E, N, S, N, S, N, E, ConfidenceHigh),
		capability("MDX", []Language{LanguageMDX}, E, U, S, U, S, S, S, ConfidenceMedium),
		capability("Astro", []Language{LanguageAstro}, E, U, S, U, S, S, S, ConfidenceMedium),
		capability("Python", []Language{LanguagePython}, E, U, U, U, U, U, S, ConfidenceLow),
		capability("Java", []Language{LanguageJava}, E, U, U, U, U, U, S, ConfidenceLow),
		capability("Kotlin", []Language{LanguageKotlin}, E, U, U, U, U, U, S, ConfidenceLow),
		capability("JavaScript", []Language{LanguageJavaScript}, E, U, U, U, U, U, S, ConfidenceLow),
		capability("TypeScript", []Language{LanguageTypeScript}, E, U, U, U, U, U, S, ConfidenceLow),
		capability("JSX", []Language{LanguageJSX}, E, U, U, U, U, U, S, ConfidenceLow),
		capability("TSX", []Language{LanguageTSX}, E, U, U, U, U, U, S, ConfidenceLow),
		capability("HTML", []Language{LanguageHTML}, E, N, S, N, S, N, S, ConfidenceMedium),
		capability("XML", []Language{LanguageXML}, E, N, S, N, E, N, E, ConfidenceHigh),
		capability("XML plist", []Language{LanguageXMLPlist}, E, N, S, N, E, N, E, ConfidenceHigh),
		capability("binary plist", []Language{LanguageBinaryPlist}, E, N, U, N, U, N, U, ConfidenceLow),
		capability("CSS", []Language{LanguageCSS}, E, U, S, N, S, S, S, ConfidenceMedium),
		capability("JSON family", []Language{LanguageJSON, LanguageJSONFamily}, E, N, S, N, E, N, E, ConfidenceHigh),
		capability("YAML", []Language{LanguageYAML}, E, N, U, N, U, N, S, ConfidenceLow),
		capability("TOML", []Language{LanguageTOML}, E, N, U, N, U, N, S, ConfidenceLow),
		capability("Terraform", []Language{LanguageTerraform}, E, U, U, U, U, S, S, ConfidenceLow),
		capability("Gradle", []Language{LanguageGradle}, E, U, U, U, U, S, S, ConfidenceLow),
		capability("SQL", []Language{LanguageSQL}, E, U, U, U, U, S, S, ConfidenceLow),
		capability("shell", []Language{LanguageBash, LanguageZsh, LanguagePOSIXShell}, E, U, U, U, U, S, S, ConfidenceLow),
		capability("Dockerfile", []Language{LanguageDockerfile}, E, S, S, N, N, E, E, ConfidenceHigh),
		capability("Vagrantfile", []Language{LanguageVagrantfile}, E, U, U, U, U, S, S, ConfidenceLow),
	}
}

func confidenceFor(language Language) Confidence {
	switch language {
	case LanguageGo, LanguageMarkdown, LanguageXML, LanguageXMLPlist, LanguageJSON, LanguageJSONFamily, LanguageDockerfile:
		return ConfidenceHigh
	case LanguageMDX, LanguageAstro, LanguageHTML, LanguageCSS:
		return ConfidenceMedium
	default:
		return ConfidenceLow
	}
}
