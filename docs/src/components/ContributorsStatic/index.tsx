import React from 'react';
import contributors from '@site/src/data/contributors.json';

export default function ContributorsStatic() {
  return (
    <div style={{display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '16px'}}>
      {contributors.map((user) => (
        <a 
          key={user.login} 
          href={user.html_url} 
          title={`${user.login} (${user.contributions} contributions)`}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            transition: 'transform 0.2s ease-in-out',
            display: 'inline-block'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.1)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
          }}
        >
          <img 
            src={user.avatar_url} 
            alt={user.login} 
            width="50" 
            height="50" 
            style={{
              borderRadius: '50%',
              border: '2px solid #e1e4e8',
              display: 'block'
            }}
          />
        </a>
      ))}
    </div>
  );
}

