def get_moods(dbconn):
    SQL_Sentence = dbconn.cursor().execute("SELECT * FROM moods")
    results = SQL_Sentence.fetchall()
    SQL_Sentence.close()
    return results