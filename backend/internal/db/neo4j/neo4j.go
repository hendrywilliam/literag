package neo4j

import driver "github.com/neo4j/neo4j-go-driver/v5/neo4j"

func NewDriver(uri, username, password string) (driver.DriverWithContext, error) {
	return driver.NewDriverWithContext(uri, driver.BasicAuth(username, password, ""))
}
