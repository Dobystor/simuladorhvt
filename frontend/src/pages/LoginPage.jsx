import ProfileSelector from '../components/auth/ProfileSelector';
import LoginForm from '../components/auth/LoginForm';

export default function LoginPage() {
  return (
    <div className="login-wrap">
      <div className="panel">
        <h2 style={{ marginTop: 0 }}>Haulage Event Simulator</h2>
        <p className="muted">Select a server and sign in with your SmartFlow credentials.</p>
        <ProfileSelector />
        <LoginForm />
      </div>
    </div>
  );
}
