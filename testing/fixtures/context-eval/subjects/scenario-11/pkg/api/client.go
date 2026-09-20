package api

// Client is intentionally small; the review task evaluates test readiness.
type Client struct{}

func (Client) Get() ([]byte, error) {
    return nil, nil
}
