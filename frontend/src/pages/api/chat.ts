import type { APIRoute } from 'astro';
import { Groq } from 'groq-sdk';
import { Pool } from 'pg';
import OpenAI from 'openai';

export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.text();
    const { message } = JSON.parse(body);

    // Initialize OpenAI for embeddings

    const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});
// Initialize Groq for chat
const groq = new Groq({
  apiKey: process.env.GROQ_API_KEY,
});
// Initialize database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

    
    // Generate embedding for the user message using OpenAI
    const embedding_response = await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: message,
    });

    const user_embedding = embedding_response.data[0].embedding;

    // Search for similar content in NeonDB
    const result = await pool.query(
      `SELECT content, source FROM embeddings 
       ORDER BY embedding <-> $1::vector LIMIT 5`,
      [JSON.stringify(user_embedding)]
    );

    const context = result.rows.map((row: any) => row.content).join('\n');

    // Generate response using Groq
    const chat_completion = await groq.chat.completions.create({
      messages: [
        {
          role: 'system',
          content: `You are a digital clone of Afaque Riaz Ahmed. Answer questions based on the following context about them:\n\n${context}`,
        },
        {
          role: 'user',
          content: message,
        },
      ],
      model: 'llama-3.3-70b-versatile',
    });

    await pool.end();

    return new Response(
      JSON.stringify({
        reply: chat_completion.choices[0].message.content,
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('Error:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to process message', details: String(error) }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
};
