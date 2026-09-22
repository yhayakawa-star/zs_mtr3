DROP database if exists zs_mtr_db3 ;
create database zs_mtr_db3 CHARACTER SET utf8;
USE `zs_mtr_db3`;

DROP TABLE IF EXISTS `host_index`;
CREATE TABLE `host_index` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `ts` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  'dc` varchar(255) NOT NULL,
  `hostname` varchar(255) NOT NULL,
  `hostname_ip` varchar(255) NOT NULL,
  `ipzscaler` text NOT NULL,
  `sme`      varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE (`hostname`, `hostname_ip`, `sme`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `curl`;
-- time_namelookup:([\d\.]+),time_connect:([\d\.]+),speed_download:([\d\.]+),time_appconnect:([\d\.]+),time_starttransfer:([\d\.]+),time_total:([\d\.]+)')
CREATE TABLE `curl` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `ts` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `ifconfig` text NOT NULL,
  `dateid` BIGINT NOT NULL,   -- same as dir
  `dir` varchar(255) NOT NULL,  -- parent dir
  `name` varchar(255) NOT NULL, -- filename
  `host_index` BIGINT NOT NULL, --
  `url` varchar(255) NOT NULL, -- url
  `http_code` int not null,
  `time_namelookup` float not null,
  `time_connect` float not null, 
  `speed_download` float not null,
  `time_appconnect` float not null,
  `time_starttransfer` float not null,
  `time_total` float not null,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `mtr`;
CREATE TABLE `mtr` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `ts` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `ifconfig` text NOT NULL,
  `dir` varchar(255) NOT NULL,  -- parent dir
  `name` varchar(255) NOT NULL, -- filename
  `host_index` BIGINT NOT NULL, -- 
  `host`text not NULL, --  from hostname in MTR result
  `mtr_option` varchar(255) NOT NULL,  -- mtr <option> <dest> -- line -rnc300
  `dest` varchar(255) NOT NULL,      -- mtr <option> <dest>
  `start_date` varchar(255) NOT NULL,   -- Start: in MTR result file, e.g 2024-03-19
  `start_time` varchar(255) NOT NULL,   -- Start: in MTR result file, e.g 09:25:01
  `tz` int(5) NOT NULL,  -- +0900 to int
  `dateid` BIGINT NOT NULL,   -- from start+tx to dateid
  PRIMARY KEY (`id`),
  UNIQUE (`dir`, `name`, `host_index`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

DROP TABLE IF EXISTS `mtr_node`;
CREATE TABLE `mtr_node` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `mtr_index` BIGINT NOT NULL,
  `idx` int(11) NOT NULL, -- hop #
  `node` varchar(256) NOT NULL, -- IP or ???
  `loss` float(4,1) NOT NULL,
  `snt` int(11) NOT NULL,
  `last` float(5,1) NOT NULL,
  `ave` float(5,1) NOT NULL,
  `best` float(5,1) NOT NULL,
  `wrst` float(5,1) NOT NULL,
  `stdev` float(5,1) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
ALTER TABLE `mtr_node` 
  MODIFY `last` FLOAT NOT NULL,
  MODIFY `ave` FLOAT NOT NULL,
  MODIFY `best` FLOAT NOT NULL,
  MODIFY `wrst` FLOAT NOT NULL,
  MODIFY `stdev` FLOAT NOT NULL;

DROP TABLE IF EXISTS `mtr_node_ip`;
CREATE TABLE `mtr_node_ip` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `mtr_node_id` BIGINT NOT NULL,
  `node` varchar(256) NOT NULL, -- IP or ???
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
ALTER TABLE mtr_node_ip ADD INDEX mtr_node_id_index (mtr_node_id);


-- ALTER TABLE mtr_node MODIFY `wrst` float(6,1);

create index mtr_host_index on mtr (host_index);
create index mtr_node_index on mtr_node (mtr_index);
create index mtr_dateid_index on mtr (dateid);




create user 'mtr'@'localhost' identified by 'Passwd88!';
set password for 'mtr'@'localhost' = 'Passwd88!';
GRANT ALL on zs_mtr_db3.* TO 'mtr'@'localhost';
ALTER USER 'mtr'@'localhost' IDENTIFIED WITH mysql_native_password BY 'Passwd88!';

create user 'mtr'@'127.0.0.1' identified by 'Passwd88!';
ALTER USER 'mtr'@'127.0.0.1' IDENTIFIED BY 'Passwd88!';
GRANT ALL on zs_mtr_db3.* TO 'mtr'@'127.0.0.1';


create user 'mtr'@'192.168.11.164' identified by 'Passwd88!';
GRANT ALL on zs_mtr_db3.* TO 'trust'@'192.168.11.164';

create user 'mtr'@'centos83-163' identified by 'Passwd88!';
GRANT ALL on zs_mtr_db3.* TO 'mtr'@'centos83-163'; 

create user 'mtr'@'192.168.11.168' identified by 'Passwd88!';
GRANT ALL on zs_mtr_db3.* TO 'mtr'@'192.168.11.168';
ALTER USER 'mtr'@'192.168.11.168' IDENTIFIED WITH mysql_native_password BY 'Passwd88!';

create user 'mtr'@'192.168.11.170' identified by 'Passwd88!';
GRANT ALL on zs_mtr_db3.* TO 'mtr'@'192.168.11.170';

create user 'mtr'@'192.168.11.168' identified by 'Passwd88!';
GRANT ALL on zs_mtr_db3.* TO 'mtr'@'192.168.11.168';

create user 'mtr'@'host-5.skytap.example' identified by 'Passwd88!';
GRANT ALL on zs_mtr_db3.* TO 'mtr'@'host-5.skytap.example';

create user 'mtr'@'210.138.60.132' identified by 'Passwd88!';
GRANT ALL on zs_mtr_db3.* TO 'mtr'@'210.138.60.132';

create user 'mtr'@'147.161.192.97' identified by 'Passwd88!';
GRANT ALL on zs_mtr_db3.* TO 'mtr'@'147.161.192.97';

create user 'mtr'@'ip-172-31-42-107.ap-northeast-1.compute.internal' identified by 'Passwd88!';
GRANT ALL on zs_mtr_db3.* TO 'mtr'@'ip-172-31-42-107.ap-northeast-1.compute.internal';

create user 'ubuntu'@'localhost' identified by 'Passwd88!';
GRANT ALL on zs_mtr_db3.* TO 'ubuntu'@'localhost';

create user 'mtr'@'10.0.0.170' identified by 'Passwd88!';
GRANT ALL on zs_mtr_db3.* TO 'mtr'@'10.0.0.170'