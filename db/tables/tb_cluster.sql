DROP TABLE IF EXISTS tb_cluster;

CREATE TABLE IF NOT EXISTS tb_cluster (
    descClusterName VARCHAR(150),
    idCluster VARCHAR(250),
    flAutoOnOff INT,
    vlStartOn INT,
    vlStopOn INT
);
