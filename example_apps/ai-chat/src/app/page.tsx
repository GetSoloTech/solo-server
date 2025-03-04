'use client';

import { useState, useRef, useEffect } from 'react';

export default function Home() {
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    try {
      const response = await fetch('http://localhost:11434/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'llama3.2',
          messages: [...messages, userMessage],
        }),
      });

      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      let aiResponse = '';
      
      // Initialize assistant message immediately
      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = new TextDecoder().decode(value);
        const lines = text.split('\n').filter(line => line.trim());
        
        for (const line of lines) {
          try {
            const data = JSON.parse(line);
            if (data.message?.content) {
              aiResponse += data.message.content;
              
              // Update the last message with new content
              setMessages(prev => {
                const newMessages = [...prev];
                const lastMessage = newMessages[newMessages.length - 1];
                if (lastMessage && lastMessage.role === 'assistant') {
                  lastMessage.content = aiResponse;
                  return [...newMessages];
                }
                return prev;
              });
            }
          } catch (e) {
            console.error('Error parsing JSON:', e);
          }
        }
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, there was an error processing your request.' }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <main className="flex justify-center items-center min-h-screen p-4 bg-gray-50">
      <div className="w-full max-w-3xl bg-white rounded-xl shadow-lg overflow-hidden flex flex-col h-[80vh]">
        {/* Header */}
        <div className="bg-primary p-4 text-white">
          <h1 className="text-xl font-semibold">AI Frontend Assistant</h1>
          <p className="text-sm opacity-80">Ask any frontend development questions</p>
        </div>
        
        {/* Messages Area */}
        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 my-8">
              <p className="text-lg font-medium">Welcome to the AI Frontend Assistant!</p>
              <p className="mt-2">Ask any questions about frontend development, React, CSS, JavaScript, and more.</p>
            </div>
          )}
          
          {messages.map((message, index) => (
            <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={message.role === 'user' ? 'user-bubble' : 'ai-bubble'}>
                {message.content || (
                  message.role === 'assistant' && <span className="text-gray-400">Loading...</span>
                )}
              </div>
            </div>
          ))}
          
          {isTyping && (
            <div className="flex justify-start">
              <div className="ai-bubble flex space-x-1 py-3 px-4">
                <div className="typing-dot" style={{ animationDelay: '0s' }}></div>
                <div className="typing-dot" style={{ animationDelay: '0.2s' }}></div>
                <div className="typing-dot" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        
        {/* Input Area */}
        <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200 flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a frontend question..."
            className="flex-1 py-2 px-4 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          />
          <button 
            type="submit" 
            className="bg-primary hover:bg-primary-dark text-white font-medium py-2 px-6 rounded-full transition-colors"
            disabled={isTyping}
          >
            Send
          </button>
        </form>
      </div>
    </main>
  );
}
