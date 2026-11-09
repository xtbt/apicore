-- phpMyAdmin SQL Dump
-- version 5.1.0
-- https://www.phpmyadmin.net/
--
-- Host: localhost:8889
-- Generation Time: Nov 09, 2026 at 03:54 AM
-- Server version: 5.7.32
-- PHP Version: 8.0.3

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `apicore`
--
DROP DATABASE IF EXISTS `apicore`;
CREATE DATABASE IF NOT EXISTS `apicore` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `apicore`;

-- --------------------------------------------------------

--
-- Table structure for table `moods`
--

DROP TABLE IF EXISTS `moods`;
CREATE TABLE `moods` (
  `MoodId` int(10) UNSIGNED NOT NULL,
  `MoodName` varchar(16) NOT NULL,
  `MoodStatus` enum('Active','Inactive') NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Dumping data for table `moods`
--

INSERT INTO `moods` (`MoodId`, `MoodName`, `MoodStatus`) VALUES
(6, 'Hungry', 'Inactive'),
(7, 'Bored', 'Active'),
(9, 'Scared', 'Inactive'),
(10, 'Tired', 'Active'),
(14, 'Very Sad', 'Active'),
(15, 'Very Relaxed', 'Active'),
(16, 'Fearless', 'Active'),
(17, 'Very Fearless', 'Active'),
(18, 'Motivated', 'Inactive');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `UserId` int(10) UNSIGNED NOT NULL,
  `Username` varchar(16) NOT NULL,
  `Password` varchar(255) NOT NULL,
  `Name` varchar(45) NOT NULL,
  `PaternalSurname` varchar(25) NOT NULL,
  `MaternalSurname` varchar(25) DEFAULT NULL,
  `UserStatus` enum('Active','Inactive') NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='API test users table';

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`UserId`, `Username`, `Password`, `Name`, `PaternalSurname`, `MaternalSurname`, `UserStatus`) VALUES
(1, 'test', 'd480164bc4aa430a9a97e920d5aba2ab:58fe6400cf00bac8e3cea6dc093bc8288eab4ff5d482772c85b607a6e200a171', 'test', 'test', '', 'Active'),
(2, 'qsvqgexi', '7f84d592505b431b8b1ee2bd87bd108a:6c41847673bea58541cd7157186be086e4c0e66d6ab83153115d94013bb16918', 'Sofia', 'Sánchez', '', 'Active'),
(3, 'oznic333', 'a470951b607345cba7712a7d9cd6664c:ee0fc16dd62f31747be13987278f07732c3917b1264d3d97497e2346f551b81d', 'Ana', 'Torres', '', 'Active'),
(4, '8tecjxjm', '43eef114bdcb47899fb42d7c911f553c:6fdb605b247fd680f53eafd432011880b8080261c62399a1ec32c851b4748fe7', 'Laura', 'Martínez', '', 'Active'),
(5, 'a6re9szi', '975d64e43fad4ba897fcf87891a6abf4:4f2ac0d5b65b86a4543ba716bcc44d5928e93b9d6645c7877ae4858257590187', 'Pedro', 'Torres', '', 'Active'),
(6, '6eo5sey5', '86b3bb2ca4ea415591dc87f6087a0ae9:723e52642cf44bf25f1ea3e4942320a2380f1a35abb1058e382f09d3407fb517', 'Sofia', 'López', '', 'Active'),
(7, 'tijuana', '3edf79fe1bc14e3c822c0c8dfa8a37cf:7b46f20f4d1020380218a62464e42977278a240b3deda701dfff5ff8f9d48956', 'tijuana', 'tijuana', '', 'Active');

-- --------------------------------------------------------

--
-- Table structure for table `users_tokens`
--

DROP TABLE IF EXISTS `users_tokens`;
CREATE TABLE `users_tokens` (
  `TokenId` int(10) UNSIGNED NOT NULL,
  `UserId` int(10) UNSIGNED NOT NULL,
  `TokenHash` varchar(255) NOT NULL,
  `TokenExpiration` datetime NOT NULL,
  `TokenCreatedAt` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Token table';

--
-- Indexes for dumped tables
--

--
-- Indexes for table `moods`
--
ALTER TABLE `moods`
  ADD PRIMARY KEY (`MoodId`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`UserId`),
  ADD UNIQUE KEY `Username` (`Username`);

ALTER TABLE `users_tokens`
  ADD PRIMARY KEY (`TokenId`),
  ADD UNIQUE KEY `TokenHash` (`TokenHash`),
  ADD KEY `UserId` (`UserId`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `moods`
--
ALTER TABLE `moods`
  MODIFY `MoodId` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=20;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `UserId` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

ALTER TABLE `users_tokens`
  MODIFY `TokenId` int(10) UNSIGNED NOT NULL AUTO_INCREMENT;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
