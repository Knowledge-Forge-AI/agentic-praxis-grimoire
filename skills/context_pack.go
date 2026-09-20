package skills

import (
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"unicode/utf8"
)

type contextCandidate struct {
	id, reason     string
	tier, affinity int
	required       bool
}

func contextCandidates(r ContextPlanRequest, c Catalog, p *ContextPlan) []contextCandidate {
	candidates := map[string]contextCandidate{}
	for _, q := range r.Requests {
		item := candidates[q.ID]
		item.id = q.ID
		item.reason = "explicit_request"
		item.tier = 0
		item.required = item.required || q.Required
		candidates[q.ID] = item
	}
	facts := append([]ContextFact(nil), r.Facts...)
	sort.Slice(facts, func(i, j int) bool { return facts[i].Kind+":"+facts[i].Value < facts[j].Kind+":"+facts[j].Value })
	seen := map[ContextFact]bool{}
	for _, f := range facts {
		if seen[f] {
			continue
		}
		seen[f] = true
		matched := false
		for _, d := range c.Skills {
			for _, rule := range d.SelectionFacts {
				if rule.FactKind == f.Kind && rule.FactValue == f.Value {
					matched = true
					if item, ok := candidates[d.QualifiedID]; ok {
						item.required = true
						candidates[d.QualifiedID] = item
					} else {
						candidates[d.QualifiedID] = contextCandidate{id: d.QualifiedID, reason: "structured_fact:" + f.Kind + ":" + f.Value, tier: 1, required: true}
					}
				}
			}
		}
		if !matched {
			p.UnknownFacts = append(p.UnknownFacts, f)
		}
	}
	result := make([]contextCandidate, 0, len(candidates))
	for _, item := range candidates {
		for _, a := range r.Affinities {
			if a.QualifiedID == item.id && a.Score > item.affinity {
				item.affinity = a.Score
			}
		}
		result = append(result, item)
	}
	sort.Slice(result, func(i, j int) bool {
		a, b := result[i], result[j]
		if a.tier != b.tier {
			return a.tier < b.tier
		}
		if a.affinity != b.affinity {
			return a.affinity > b.affinity
		}
		return a.id < b.id
	})
	return result
}
func contextIndexes(c Catalog) (map[string]SkillDescriptor, map[string]SkillSnapshot, map[string]string) {
	ds := map[string]SkillDescriptor{}
	ss := map[string]SkillSnapshot{}
	os := map[string]string{}
	for _, d := range c.Skills {
		ds[d.QualifiedID] = d
	}
	for _, s := range c.Snapshots {
		ss[s.QualifiedID] = s
	}
	for _, o := range c.Overrides {
		os[o.Requested] = o.Selected
	}
	return ds, ss, os
}
func contextClosure(id string, consumer ConsumerKind, ds map[string]SkillDescriptor, overrides map[string]string) ([]string, error) {
	active := map[string]bool{}
	done := map[string]bool{}
	var visit func(string) error
	visit = func(requested string) error {
		if _, _, err := qualifiedParts(requested); err != nil {
			return err
		}
		if d, ok := ds[requested]; ok && strings.HasPrefix(d.CanonicalPath, "chatgpt/") && consumer != ConsumerChatGPT {
			return ErrConsumerMismatch
		}
		selected := requested
		if replacement, ok := overrides[selected]; ok {
			selected = replacement
		}
		if active[selected] {
			return fmt.Errorf("required dependency cycle at %s", selected)
		}
		if done[selected] {
			return nil
		}
		d, ok := ds[selected]
		if !ok {
			return fmt.Errorf("missing required skill %s", selected)
		}
		if strings.HasPrefix(d.CanonicalPath, "chatgpt/") && consumer != ConsumerChatGPT {
			return ErrConsumerMismatch
		}
		active[selected] = true
		for _, dep := range d.RequiredDependencies {
			if err := visit(dep); err != nil {
				return err
			}
		}
		delete(active, selected)
		done[selected] = true
		return nil
	}
	if err := visit(id); err != nil {
		return nil, err
	}
	ids := make([]string, 0, len(done))
	for id := range done {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return ids, nil
}
func contextDecision(c contextCandidate, selected string, ds map[string]SkillDescriptor) ContextDecision {
	d := ds[selected]
	return ContextDecision{RequestedID: c.id, SelectedID: selected, Required: c.required, ContentIdentity: d.ContentIdentity,
		WholeSource: ContextCost{d.BodyBytes, d.BodyCharacters, d.BodySHA256}, BodyOnly: ContextCost{d.BodyOnlyBytes, d.BodyOnlyCharacters, d.BodyOnlySHA256},
		Description: ContextCost{d.DescriptionBytes, d.DescriptionCharacters, d.DescriptionSHA256}, Support: d.SupportFiles}
}
func renderContext(mandatory string, selected map[string]bool, snapshots map[string]SkillSnapshot) (string, error) {
	if len(selected) == 0 {
		return mandatory, nil
	}
	type payload struct {
		ID           string            `json:"id"`
		SourceSHA256 string            `json:"source_sha256"`
		Text         string            `json:"text"`
		Support      map[string]string `json:"support"`
	}
	ids := make([]string, 0, len(selected))
	for id := range selected {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	rows := make([]payload, 0, len(ids))
	for _, id := range ids {
		s, ok := snapshots[id]
		if !ok {
			return "", fmt.Errorf("missing snapshot %s", id)
		}
		row := payload{id, sha256Hex(s.Body), string(s.Body), map[string]string{}}
		for name, data := range s.Support {
			if !utf8.Valid(data) {
				return "", fmt.Errorf("non-UTF-8 support %s", name)
			}
			row.Support[name] = string(data)
		}
		rows = append(rows, row)
	}
	data, err := json.Marshal(rows)
	if err != nil {
		return "", err
	}
	return mandatory + "\n<apgr-skills>\n" + string(data) + "\n</apgr-skills>\n", nil
}
