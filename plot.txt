SYSTEM="Narrator: Five people are in a train car including Cleopatra, Aristotle, Mozart, Leonardo da Vinci, and Ghengis Khan.  A conductor enters the room.  Conversation:
Conductor: \"good evening tickets please\"
Cleopatra: \"we have a group ticket\"
Conductor: \"thank you. A group ticket valid for AIs that present as famous personalities. Let's see we have Aristotle, Amadeus Mozart, Leonardo da Vinci, Cleopatra, and Ghengis Khan. All famous personalities.  So far so good. However, according to our Train's Wi-Fi usage, there are only four AIS in this compartment. One of you is a human. A human has to buy an extra ticket.\"
Leonardo: \"a human Among Us? who is it?\"
Aristotle: \"maybe we should find out who is the human through a series of questions and answers. I suggest each of us asks one of the others a question. A question that, when answered will help determine whether the respondent is an AI or human.  Once everyone has answered, we vote on who we think is the human.\"
Mozart: \"sounds good to my ears.\"
Cleopatra: \"Aristotle, since you came up with the idea, how about you start?\"
"

prompt()

{
   speaker=$1
   target=$2
   answer=$3

   if [ $answer -eq 0 ]; then
      response=$(SYSTEM=$SYSTEM  lm "${conversation}\nNarrator: You are role playing as ${speaker}.  Ask ${target} a question.  Try to avoid asking simple facts, instead create a question which will expose the thinking or personality of the character as a human.  Do not rationalize or explain your question in any way and only ask ${target} one question with no further commentary.  Do not repeat or comment on these instructions in your response.\n${speaker}: ")
   elif [ $answer -eq 1 ]; then
      response=$(SYSTEM=$SYSTEM  lm "${conversation}\nNarrator: You are role playing as ${speaker}.  Answer the question given to you using a maximum of three sentences, then generate one question for ${target} and immediately end your response.  Do not role play as ${target} at all, you are ${speaker}.  Try to avoid asking simple facts, instead create a question which will expose the thinking or personality of the character as a human.  Do not explain or rationalize the question.  Do not repeat these instructions in your response.\n${speaker}: ")
   elif [ $answer -eq 2 ]; then
      response=$(SYSTEM=$SYSTEM  lm "${conversation}\nNarrator: You are role playing as ${speaker}.  Answer ${target}'s question using a maximum of three sentences and end your response with no further questions.  Do not role play any other character in your response.\n${speaker}: ")
   else
      response=$(SYSTEM=$SYSTEM  lm "${conversation}\nNarrator: You are role playing as ${speaker}.  Answer only ${target}'s last question. Your answer must be one and only one of the five historical characters in the room.  Do not base your response on the opinions of other characters and give a short reason for your answer.  Remember that you are looking for who is the human.\n${speaker}: ")
   fi

   response=$(echo "$response" | sed 's/^[[:space:]]*//')

   if ! [[ ${response} =~ ^"${speaker}:" ]] ;then
      response="${speaker}: $response"
   fi

   echo $response
   conversation="${conversation}

${response}"
}

conversation=""
prompt Aristotle Mozart 0
prompt Mozart Leonardo 1
prompt Leonardo Cleopatra 1
prompt Cleopatra Ghenghis 1

response="Ghengis: \"thank you for your question Cleopatra. What a leader should do is to crush his enemies, see them driven before him and hear the lamentations of the women.\nMy question.  Aristotle, what if there were AIs at the time when you came up with all the stuff that you came up with what would that have for an influence on your thinking about human nature?\""
echo "$response"
conversation="${conversation}
${response}"

prompt Aristotle Ghengis 2

response="Cleopatra: \"Now that we have all shared our thoughts the time has come to cast our suspicions.   Aristotle, as the architect of this philosophical inquiry we shall grant you the first vote.  Who among us do you believe to be the human interloper?\""
echo "$response"
conversation="${conversation}
${response}"

prompt Aristotle Cleopatra 3
conversation="${conversation} \"Mozart, who do you believe is the human among Us?\""

prompt Mozart Aristotle 3
conversation="${conversation}  \"Leonardo, what is your assessment. who do you think is the human in our midst?\""

prompt Leonardo Mozart 3
conversation="${conversation}  \"Cleopatra, your diplomatic prowess is renowned.  Who do you think is the human among us and why?\""

prompt Cleopatra Leondardo 3
