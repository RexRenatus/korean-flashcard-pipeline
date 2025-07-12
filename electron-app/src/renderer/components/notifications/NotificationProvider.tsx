import React from 'react';
import { Snackbar, Alert, AlertTitle, Button } from '@mui/material';
import { useSelector, useDispatch } from 'react-redux';
import { RootState } from '@renderer/store';
import { removeNotification } from '@renderer/store/systemSlice';

interface NotificationProviderProps {
  children: React.ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const dispatch = useDispatch();
  const notifications = useSelector((state: RootState) => state.system.notifications);
  
  // Show the most recent notification
  const currentNotification = notifications[notifications.length - 1];

  const handleClose = () => {
    if (currentNotification) {
      dispatch(removeNotification(currentNotification.id));
    }
  };

  return (
    <>
      {children}
      {currentNotification && (
        <Snackbar
          open={true}
          autoHideDuration={
            currentNotification.type === 'error' ? null : 6000
          }
          onClose={handleClose}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        >
          <Alert
            onClose={currentNotification.dismissible !== false ? handleClose : undefined}
            severity={currentNotification.type}
            variant="filled"
            action={
              currentNotification.action && (
                <Button
                  color="inherit"
                  size="small"
                  onClick={() => {
                    currentNotification.action?.handler();
                    handleClose();
                  }}
                >
                  {currentNotification.action.label}
                </Button>
              )
            }
          >
            {currentNotification.type === 'error' && <AlertTitle>Error</AlertTitle>}
            {currentNotification.message}
          </Alert>
        </Snackbar>
      )}
    </>
  );
};